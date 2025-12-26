"""
Prompt loader - loads and renders prompt templates from YAML files.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field

from ..config import settings


class PromptVariable(BaseModel):
    """Schema for a prompt variable."""

    name: str
    description: str = ""
    schema: Optional[Dict[str, Any]] = None


class PromptTemplate(BaseModel):
    """Loaded prompt template."""

    version: str = "0.1.0"
    prompt_type: str
    tools: List[Dict[str, Any]] = Field(default_factory=list)
    variables: List[PromptVariable] = Field(default_factory=list)
    role: str = ""
    instruction: str = ""
    response_type: str = "JSON"
    response_schema: Optional[Dict[str, Any]] = None


class PromptLoader:
    """
    Loads and renders prompt templates from YAML files.
    
    Supports template variables with {var_json} syntax for JSON serialization.
    """

    def __init__(self, prompts_dir: str | None = None):
        """
        Initialize prompt loader.
        
        Args:
            prompts_dir: Directory containing prompt YAML files.
        """
        self._prompts_dir = Path(prompts_dir or settings.PROMPTS_DIR)
        self._cache: Dict[str, PromptTemplate] = {}

    def load(self, prompt_name: str) -> PromptTemplate:
        """
        Load a prompt template by name.
        
        Args:
            prompt_name: Name of the prompt (without .yaml extension).
            
        Returns:
            Loaded prompt template.
            
        Raises:
            FileNotFoundError: If prompt file doesn't exist.
        """
        if prompt_name in self._cache:
            return self._cache[prompt_name]
        
        # Handle both with and without .yaml extension
        file_name = prompt_name if prompt_name.endswith(".yaml") else f"{prompt_name}.yaml"
        file_path = self._prompts_dir / file_name
        
        if not file_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {file_path}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        # Parse variables
        variables = []
        for var_data in data.get("variables", []):
            variables.append(PromptVariable(
                name=var_data.get("name", ""),
                description=var_data.get("description", ""),
                schema=var_data.get("schema"),
            ))
        
        template = PromptTemplate(
            version=data.get("version", "0.1.0"),
            prompt_type=data.get("prompt_type", prompt_name),
            tools=data.get("tools", []),
            variables=variables,
            role=data.get("role", "").strip(),
            instruction=data.get("instruction", "").strip(),
            response_type=data.get("response_type", "JSON"),
            response_schema=data.get("response_schema"),
        )
        
        self._cache[prompt_name] = template
        return template

    def render(
        self,
        template: PromptTemplate,
        variables: Dict[str, Any],
    ) -> tuple[str, str]:
        """
        Render a prompt template with variables.
        
        Args:
            template: The prompt template.
            variables: Variable values to substitute.
            
        Returns:
            Tuple of (system_prompt, user_prompt).
        """
        # System prompt is the role
        system_prompt = template.role.strip()
        
        # User prompt is the instruction with variables substituted
        user_prompt = self._substitute_variables(template.instruction, variables)
        
        return system_prompt, user_prompt

    def _substitute_variables(
        self,
        text: str,
        variables: Dict[str, Any],
    ) -> str:
        """
        Substitute variables in text.
        
        Handles patterns like:
        - {variable_name} - direct substitution
        - {variable_name_json} - JSON serialized substitution
        
        Args:
            text: Template text.
            variables: Variable values.
            
        Returns:
            Text with variables substituted.
        """
        result = text
        
        # Find all {var_name} patterns
        pattern = r"\{(\w+?)(?:_json)?\}"
        matches = re.findall(pattern, text)
        
        for var_name in set(matches):
            # Try both with and without _json suffix
            json_pattern = f"{{{var_name}_json}}"
            plain_pattern = f"{{{var_name}}}"
            
            value = variables.get(var_name)
            
            if json_pattern in result:
                # JSON serialized substitution
                if value is not None:
                    json_value = json.dumps(value, ensure_ascii=False, indent=2)
                else:
                    json_value = "null"
                result = result.replace(json_pattern, json_value)
            
            if plain_pattern in result:
                # Plain substitution
                if value is not None:
                    if isinstance(value, (dict, list)):
                        str_value = json.dumps(value, ensure_ascii=False)
                    else:
                        str_value = str(value)
                else:
                    str_value = ""
                result = result.replace(plain_pattern, str_value)
        
        return result

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._cache.clear()


# Global prompt loader instance
_prompt_loader: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """Get the global prompt loader instance."""
    global _prompt_loader
    if _prompt_loader is None:
        _prompt_loader = PromptLoader()
    return _prompt_loader

