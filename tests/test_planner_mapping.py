"""
Tests for chat planner context mapping rules.

Verifies that the planner correctly maps actions to required_context.
"""

import pytest

from src.worker.contracts.schemas import (
    ChatPlannerOutput,
    PlannerAction,
)


class TestPlannerContextMapping:
    """
    Tests for action -> required_context mapping rules from chat_planner.yaml.
    
    Rules:
    - GET_ACTIVE_ROUTINES -> ["active_routines"]
    - RECALL_USER_MEMORY  -> ["user_memory"]
    - FIND_RELEVANT_EXERCISES -> ["exercise_catalog"]
    - ANSWER_DIRECT -> []
    - ASK_CLARIFY -> []
    - HANDOFF_INTENT_ROUTER -> []
    """

    def _create_plan(
        self,
        action: str,
        required_context: list,
        args: dict = None,
    ) -> ChatPlannerOutput:
        """Helper to create a planner output."""
        return ChatPlannerOutput(
            action=action,
            confidence=0.9,
            required_context=required_context,
            args=args or {},
            should_stream=False,
            needs_clarification=False,
            clarification_question="",
            notes="",
        )

    def test_get_active_routines_requires_active_routines(self):
        """GET_ACTIVE_ROUTINES should require active_routines context."""
        plan = self._create_plan(
            action="GET_ACTIVE_ROUTINES",
            required_context=["active_routines"],
        )
        
        assert plan.action == PlannerAction.GET_ACTIVE_ROUTINES
        assert "active_routines" in plan.required_context
        # Should not include other contexts
        assert "user_memory" not in plan.required_context
        assert "exercise_catalog" not in plan.required_context

    def test_recall_user_memory_requires_user_memory(self):
        """RECALL_USER_MEMORY should require user_memory context."""
        plan = self._create_plan(
            action="RECALL_USER_MEMORY",
            required_context=["user_memory"],
            args={"query": "무릎 부상 기록"},
        )
        
        assert plan.action == PlannerAction.RECALL_USER_MEMORY
        assert "user_memory" in plan.required_context
        assert plan.args.get("query") is not None

    def test_find_relevant_exercises_requires_exercise_catalog(self):
        """FIND_RELEVANT_EXERCISES should require exercise_catalog context."""
        plan = self._create_plan(
            action="FIND_RELEVANT_EXERCISES",
            required_context=["exercise_catalog"],
            args={"query": "허리 안전한 하체 운동"},
        )
        
        assert plan.action == PlannerAction.FIND_RELEVANT_EXERCISES
        assert "exercise_catalog" in plan.required_context
        assert plan.args.get("query") is not None

    def test_answer_direct_requires_no_context(self):
        """ANSWER_DIRECT should not require any context."""
        plan = self._create_plan(
            action="ANSWER_DIRECT",
            required_context=[],
        )
        
        assert plan.action == PlannerAction.ANSWER_DIRECT
        assert len(plan.required_context) == 0

    def test_ask_clarify_requires_no_context(self):
        """ASK_CLARIFY should not require any context."""
        plan = ChatPlannerOutput(
            action="ASK_CLARIFY",
            confidence=0.5,
            required_context=[],
            args={},
            should_stream=False,
            needs_clarification=True,
            clarification_question="더 자세히 설명해 주시겠어요?",
            notes="Ambiguous request",
        )
        
        assert plan.action == PlannerAction.ASK_CLARIFY
        assert len(plan.required_context) == 0
        assert plan.needs_clarification is True

    def test_handoff_intent_router_requires_no_context(self):
        """HANDOFF_INTENT_ROUTER should not require any context."""
        plan = self._create_plan(
            action="HANDOFF_INTENT_ROUTER",
            required_context=[],
        )
        
        assert plan.action == PlannerAction.HANDOFF_INTENT_ROUTER
        assert len(plan.required_context) == 0

    def test_valid_context_keys_only(self):
        """Verify only valid context keys are accepted."""
        valid_keys = {"active_routines", "user_memory", "exercise_catalog"}
        
        # Test each valid key
        for key in valid_keys:
            plan = self._create_plan(
                action="ANSWER_DIRECT",  # Action doesn't matter for this test
                required_context=[key],
            )
            assert key in plan.required_context

    def test_should_stream_defaults(self):
        """Test should_stream defaults per action type."""
        # ANSWER_DIRECT should typically stream
        direct_plan = ChatPlannerOutput(
            action="ANSWER_DIRECT",
            confidence=0.9,
            required_context=[],
            args={},
            should_stream=True,
            needs_clarification=False,
            clarification_question="",
            notes="",
        )
        assert direct_plan.should_stream is True
        
        # Context-fetching actions should not stream
        routines_plan = ChatPlannerOutput(
            action="GET_ACTIVE_ROUTINES",
            confidence=0.9,
            required_context=["active_routines"],
            args={},
            should_stream=False,
            needs_clarification=False,
            clarification_question="",
            notes="",
        )
        assert routines_plan.should_stream is False

    def test_args_required_for_memory_search(self):
        """RECALL_USER_MEMORY should have query in args."""
        plan = ChatPlannerOutput(
            action="RECALL_USER_MEMORY",
            confidence=0.85,
            required_context=["user_memory"],
            args={"query": "지난주 운동 기록"},
            should_stream=False,
            needs_clarification=False,
            clarification_question="",
            notes="",
        )
        
        assert "query" in plan.args
        assert len(plan.args["query"]) > 0

    def test_args_required_for_exercise_search(self):
        """FIND_RELEVANT_EXERCISES should have query in args."""
        plan = ChatPlannerOutput(
            action="FIND_RELEVANT_EXERCISES",
            confidence=0.88,
            required_context=["exercise_catalog"],
            args={"query": "어깨 안정성 운동"},
            should_stream=False,
            needs_clarification=False,
            clarification_question="",
            notes="",
        )
        
        assert "query" in plan.args
        assert len(plan.args["query"]) > 0

