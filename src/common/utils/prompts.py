"""Dynamic YAML prompt loader with caching and auto-discovery."""

import os
from pathlib import Path
from typing import Dict, List, Optional
import yaml
from loguru import logger

from src.config import get_config


class PromptLoader:
    """Dynamic prompt loader that auto-discovers YAML files."""
    
    def __init__(self, prompts_dir: Optional[str] = None):
        """Initialize the prompt loader.
        
        Args:
            prompts_dir: Directory containing prompt YAML files.
                        If None, uses config value.
        """
        config = get_config()
        self.prompts_dir = Path(prompts_dir or config.prompts_directory)
        self._cache: Dict[str, dict] = {}
        self._discover_prompts()
    
    def _discover_prompts(self) -> None:
        """Discover all YAML files in the prompts directory."""
        if not self.prompts_dir.exists():
            logger.warning(f"Prompts directory not found: {self.prompts_dir}")
            return
        
        yaml_files = list(self.prompts_dir.glob("*.yaml")) + list(self.prompts_dir.glob("*.yml"))
        logger.info(f"Discovered {len(yaml_files)} prompt files in {self.prompts_dir}")
        
        for yaml_file in yaml_files:
            prompt_key = yaml_file.stem  # filename without extension
            logger.debug(f"Registered prompt key: {prompt_key}")
    
    def load_prompt(self, prompt_key: str) -> dict:
        """Load a prompt by key (cached).
        
        Args:
            prompt_key: The prompt key (filename without extension).
            
        Returns:
            Dict containing the parsed YAML content.
            
        Raises:
            FileNotFoundError: If prompt file doesn't exist.
            yaml.YAMLError: If YAML parsing fails.
        """
        # Check cache first
        if prompt_key in self._cache:
            logger.debug(f"Returning cached prompt: {prompt_key}")
            return self._cache[prompt_key]
        
        # Try to load from file
        yaml_path = self.prompts_dir / f"{prompt_key}.yaml"
        if not yaml_path.exists():
            yaml_path = self.prompts_dir / f"{prompt_key}.yml"
        
        if not yaml_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_key}")
        
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                prompt_data = yaml.safe_load(f)
            
            # Cache the loaded prompt
            self._cache[prompt_key] = prompt_data
            logger.info(f"Loaded prompt: {prompt_key} from {yaml_path}")
            return prompt_data
            
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML for {prompt_key}: {e}")
            raise
    
    def list_prompts(self) -> List[str]:
        """List all available prompt keys.
        
        Returns:
            List of prompt keys (filenames without extensions).
        """
        if not self.prompts_dir.exists():
            return []
        
        yaml_files = list(self.prompts_dir.glob("*.yaml")) + list(self.prompts_dir.glob("*.yml"))
        return sorted([f.stem for f in yaml_files])
    
    def reload_prompt(self, prompt_key: str) -> dict:
        """Force reload a prompt from disk.
        
        Args:
            prompt_key: The prompt key to reload.
            
        Returns:
            Dict containing the parsed YAML content.
        """
        # Clear from cache
        if prompt_key in self._cache:
            del self._cache[prompt_key]
        
        # Load fresh
        return self.load_prompt(prompt_key)
    
    def clear_cache(self) -> None:
        """Clear all cached prompts."""
        self._cache.clear()
        logger.info("Cleared prompt cache")


# Singleton instance
_loader: Optional[PromptLoader] = None


def get_prompt_loader(prompts_dir: Optional[str] = None) -> PromptLoader:
    """Get the singleton prompt loader instance.
    
    Args:
        prompts_dir: Optional directory path. Only used on first call.
        
    Returns:
        PromptLoader instance.
    """
    global _loader
    if _loader is None:
        _loader = PromptLoader(prompts_dir=prompts_dir)
    return _loader


def load_prompt(prompt_key: str) -> dict:
    """Load a prompt by key (convenience function).
    
    Args:
        prompt_key: The prompt key to load.
        
    Returns:
        Dict containing the parsed YAML content.
    """
    loader = get_prompt_loader()
    return loader.load_prompt(prompt_key)


def list_prompts() -> List[str]:
    """List all available prompt keys (convenience function).
    
    Returns:
        List of prompt keys.
    """
    loader = get_prompt_loader()
    return loader.list_prompts()

