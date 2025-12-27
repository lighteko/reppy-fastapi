"""Prompt loading and template rendering utilities."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class PromptTemplate:
    """Loaded and parsed prompt template."""

    name: str
    version: str
    prompt_type: str
    role: str
    instruction: str
    variables: list[dict[str, Any]] = field(default_factory=list)
    tools: list[dict[str, Any]] = field(default_factory=list)
    response_type: str = "JSON"
    response_schema: dict[str, Any] = field(default_factory=dict)

    def render(self, **kwargs: Any) -> tuple[str, str]:
        """
        Render the prompt template with provided variables.
        
        Args:
            **kwargs: Variable values to substitute.
            
        Returns:
            Tuple of (system_prompt, user_instruction).
        """
        # Convert dict/list values to JSON strings
        rendered_vars: dict[str, str] = {}
        for key, value in kwargs.items():
            if isinstance(value, (dict, list)):
                rendered_vars[f"{key}_json"] = json.dumps(value, ensure_ascii=False, indent=2)
            else:
                rendered_vars[f"{key}_json"] = str(value)
            rendered_vars[key] = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)

        # Render instruction with variables
        try:
            rendered_instruction = self.instruction.format(**rendered_vars)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            rendered_instruction = self.instruction

        return self.role.strip(), rendered_instruction.strip()

    def get_schema_json(self) -> str:
        """Get response schema as JSON string."""
        return json.dumps(self.response_schema, ensure_ascii=False, indent=2)


class PromptLoader:
    """Loads and caches prompt templates from YAML files."""

    def __init__(self, prompts_dir: str | Path) -> None:
        """
        Initialize prompt loader.
        
        Args:
            prompts_dir: Directory containing prompt YAML files.
        """
        self._prompts_dir = Path(prompts_dir)
        self._cache: dict[str, PromptTemplate] = {}

    def load(self, name: str) -> PromptTemplate:
        """
        Load a prompt template by name.
        
        Args:
            name: Prompt name (without .yaml extension).
            
        Returns:
            Loaded prompt template.
            
        Raises:
            FileNotFoundError: If prompt file doesn't exist.
            ValueError: If prompt file is invalid.
        """
        if name in self._cache:
            return self._cache[name]

        # Try different file paths
        file_path = self._prompts_dir / f"{name}.yaml"
        if not file_path.exists():
            file_path = self._prompts_dir / f"{name}.yml"
        if not file_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {name}")

        try:
            with open(file_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            template = PromptTemplate(
                name=name,
                version=data.get("version", "0.0.0"),
                prompt_type=data.get("prompt_type", name),
                role=data.get("role", ""),
                instruction=data.get("instruction", ""),
                variables=data.get("variables", []),
                tools=data.get("tools", []),
                response_type=data.get("response_type", "JSON"),
                response_schema=data.get("response_schema", {}),
            )

            self._cache[name] = template
            logger.debug(f"Loaded prompt template: {name} v{template.version}")
            return template

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in prompt file {name}: {e}") from e

    def preload_all(self) -> dict[str, PromptTemplate]:
        """
        Preload all prompt templates from the directory.
        
        Returns:
            Dictionary of loaded templates.
        """
        templates: dict[str, PromptTemplate] = {}

        if not self._prompts_dir.exists():
            logger.warning(f"Prompts directory not found: {self._prompts_dir}")
            return templates

        for file_path in self._prompts_dir.glob("*.yaml"):
            name = file_path.stem
            try:
                templates[name] = self.load(name)
            except Exception as e:
                logger.error(f"Failed to load prompt {name}: {e}")

        for file_path in self._prompts_dir.glob("*.yml"):
            name = file_path.stem
            if name not in templates:
                try:
                    templates[name] = self.load(name)
                except Exception as e:
                    logger.error(f"Failed to load prompt {name}: {e}")

        return templates

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._cache.clear()

