"""Core orchestration logic for retrieval augmented generation."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Iterable

import yaml
from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter

from .clients import get_openai_client, get_qdrant_client
from .express_client import ExpressAPIClient
from .models import GenerateProgramJob, PromptTemplate, RoutineBatch, ensure_required_variables

LOGGER = logging.getLogger(__name__)


def load_prompt_template(filename: str) -> PromptTemplate:
    """Load and validate a prompt template from the prompts directory."""

    prompt_path = Path(__file__).resolve().parents[2] / "prompts" / filename
    with prompt_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if hasattr(PromptTemplate, "model_validate"):
        return PromptTemplate.model_validate(raw)  # type: ignore[attr-defined]
    return PromptTemplate.parse_obj(raw)


class RAGOrchestrator:
    """Coordinates the retrieval, prompt construction, and LLM generation steps."""

    def __init__(
        self,
        *,
        openai_client: AsyncOpenAI | None = None,
        qdrant_client: QdrantClient | None = None,
        express_client: ExpressAPIClient | None = None,
        default_collection: str | None = None,
        generation_model: str | None = None,
        embedding_model: str | None = None,
    ) -> None:
        self.openai_client = openai_client or get_openai_client()
        self.qdrant_client = qdrant_client or get_qdrant_client()
        self.express_client = express_client or ExpressAPIClient()
        self.default_collection = (
            default_collection or os.getenv("QDRANT_COLLECTION") or "exercises"
        )
        self.generation_model = generation_model or os.getenv("OPENAI_COMPLETION_MODEL") or "gpt-4o-mini"
        self.embedding_model = embedding_model or os.getenv("OPENAI_EMBEDDING_MODEL") or "text-embedding-3-large"

    async def generate_routine_from_rag(self, job: GenerateProgramJob) -> RoutineBatch:
        """Execute the full retrieval augmented workflow for a program generation job."""

        LOGGER.info("Starting RAG routine generation for user %s", job.user_id)
        user_profile = await self.express_client.get_user_profile(job.user_id)
        exercises = await self._retrieve_exercises(job)

        template = load_prompt_template("generate_routine.yaml")
        context = {
            "user_profile": user_profile,
            "job": job.prompt_context(),
            "retrieved_exercises": exercises,
        }
        ensure_required_variables(template, context.keys())

        llm_response = await self._invoke_generation(template, context)
        routine_payload = self._parse_routine_response(llm_response)
        if hasattr(RoutineBatch, "model_validate"):
            return RoutineBatch.model_validate(routine_payload)  # type: ignore[attr-defined]
        return RoutineBatch.parse_obj(routine_payload)

    async def _retrieve_exercises(self, job: GenerateProgramJob) -> list[dict[str, Any]]:
        """Embed the query, retrieve vectors from Qdrant, and hydrate exercises."""

        vector = await self._embed_query(job.build_query_text())
        collection_name = job.qdrant_collection or self.default_collection
        limit = job.top_k

        search_kwargs: dict[str, Any] = {
            "collection_name": collection_name,
            "query_vector": vector,
            "limit": limit,
        }
        metadata_filter = self._build_filter(job)
        if metadata_filter:
            search_kwargs["query_filter"] = metadata_filter

        LOGGER.debug("Searching Qdrant collection %s", collection_name)
        results = self.qdrant_client.search(**search_kwargs)
        exercise_ids = self._extract_exercise_ids(results)

        if not exercise_ids:
            LOGGER.warning("No exercises returned from Qdrant for user %s", job.user_id)
            return []

        return await self.express_client.get_exercises_by_ids(exercise_ids)

    async def _embed_query(self, text: str) -> list[float]:
        """Generate an embedding for the provided text."""

        if not text:
            raise ValueError("Cannot embed an empty query")
        response = await self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=[text],
        )
        return response.data[0].embedding

    def _build_filter(self, job: GenerateProgramJob) -> Filter | None:
        """Optionally construct a Qdrant payload filter from job metadata."""

        metadata_filters = job.metadata.get("filters") if job.metadata else None
        if not metadata_filters:
            return None
        return Filter(**metadata_filters)

    def _extract_exercise_ids(self, results: Iterable[Any]) -> list[str]:
        """Pull source identifiers out of Qdrant search results."""

        exercise_ids: list[str] = []
        for point in results:
            payload = getattr(point, "payload", None) or {}
            source_id = payload.get("source_id") or payload.get("exercise_id")
            if source_id:
                exercise_ids.append(str(source_id))
        return exercise_ids

    async def _invoke_generation(self, template: PromptTemplate, context: dict[str, Any]) -> str:
        """Invoke the completion model using the constructed prompt."""

        context_block = json.dumps(context, indent=2, ensure_ascii=False)
        response_schema = template.prompt.response_schema or {}
        schema_block = json.dumps(response_schema, indent=2, ensure_ascii=False)

        user_message = (
            f"{template.prompt.instruction.strip()}\n\n"
            f"Context:\n{context_block}\n\n"
            f"Respond with valid {template.prompt.response_type} following this schema:\n{schema_block}"
        )

        completion = await self.openai_client.chat.completions.create(
            model=self.generation_model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": template.prompt.role.strip()},
                {"role": "user", "content": user_message},
            ],
        )
        choice = completion.choices[0]
        content = getattr(choice.message, "content", None)
        if not content:
            raise RuntimeError("OpenAI completion returned no content")
        return content

    def _parse_routine_response(self, raw_response: str) -> dict[str, Any]:
        """Parse the LLM response JSON, handling code fences gracefully."""

        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = "\n".join(line for line in cleaned.splitlines() if not line.startswith("```"))
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            LOGGER.exception("Failed to decode routine JSON: %s", cleaned)
            raise ValueError("LLM response could not be parsed as JSON") from exc


async def generate_and_save(job: GenerateProgramJob) -> RoutineBatch:
    """Helper for the worker to run the full orchestrator flow."""

    orchestrator = RAGOrchestrator()
    routines = await orchestrator.generate_routine_from_rag(job)
    payload = _build_persistence_payload(job, routines)
    await orchestrator.express_client.save_batch_routines(payload)
    return routines


def _build_persistence_payload(job: GenerateProgramJob, batch: RoutineBatch) -> dict[str, Any]:
    """Convert the generated routine batch into the Express API payload shape."""

    try:
        data = batch.model_dump()  # type: ignore[attr-defined]
    except AttributeError:
        data = batch.dict()

    routines_payload: list[dict[str, Any]] = []
    for routine in data.get("routines", []):
        plans_payload: list[dict[str, Any]] = []
        for plan in routine.get("plans", []):
            sets_payload: list[dict[str, Any]] = []
            for set_item in plan.get("sets", []):
                set_payload: dict[str, Any] = {
                    "setOrder": set_item.get("set_order"),
                    "restTime": set_item.get("rest_time"),
                }
                if set_item.get("set_type_name"):
                    set_payload["setTypeName"] = set_item.get("set_type_name")
                if set_item.get("reps") is not None:
                    set_payload["reps"] = set_item.get("reps")
                if set_item.get("weight") is not None:
                    set_payload["weight"] = set_item.get("weight")
                if set_item.get("duration") is not None:
                    set_payload["duration"] = set_item.get("duration")
                sets_payload.append(set_payload)

            plan_payload: dict[str, Any] = {
                "exerciseName": plan.get("exercise_name"),
                "planOrder": plan.get("plan_order"),
                "sets": sets_payload,
            }
            if plan.get("notes"):
                plan_payload["notes"] = plan.get("notes")
            plans_payload.append(plan_payload)

        routine_payload: dict[str, Any] = {
            "routineName": routine.get("routine_name"),
            "routineOrder": routine.get("routine_order"),
            "plans": plans_payload,
        }
        if routine.get("notes"):
            routine_payload["notes"] = routine.get("notes")
        routines_payload.append(routine_payload)

    payload: dict[str, Any] = {
        "userId": job.user_id,
        "routines": routines_payload,
    }
    if job.program_id:
        payload["programId"] = job.program_id
    if data.get("program_name") or job.program_name:
        payload["programName"] = data.get("program_name") or job.program_name
    if data.get("start_date"):
        payload["startDate"] = data.get("start_date")
    if data.get("goal_date"):
        payload["goalDate"] = data.get("goal_date")
    if data.get("goal") or job.goal:
        payload["goal"] = data.get("goal") or job.goal

    return payload

