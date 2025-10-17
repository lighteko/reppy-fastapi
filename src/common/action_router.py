"""Action router for Mode A: route inputs to appropriate prompts."""

import re
from typing import Dict, List, Optional, Tuple

from loguru import logger

from src.common.prompts import list_prompts


class ActionRouter:
    """Routes user inputs to the appropriate prompt."""
    
    # Default prompt keys (the three existing ones)
    DEFAULT_PROMPTS = ["chat_response", "generate_program", "update_routine"]
    
    def __init__(self, available_prompts: Optional[List[str]] = None):
        """Initialize the router.
        
        Args:
            available_prompts: List of available prompt keys. If None, auto-discovers.
        """
        self.available_prompts = available_prompts or list_prompts()
        
        # Ensure default prompts are available
        for prompt in self.DEFAULT_PROMPTS:
            if prompt not in self.available_prompts:
                logger.warning(f"Default prompt '{prompt}' not found in available prompts")
        
        logger.info(f"Router initialized with {len(self.available_prompts)} available prompts")
    
    def _check_generate_program_rules(self, input_text: str, context: Dict) -> bool:
        """Check if input matches generate_program rules.
        
        Args:
            input_text: User input text.
            context: Additional context.
            
        Returns:
            True if rules match.
        """
        # Rule 1: Intent keywords
        keywords = [
            "generate program",
            "new block",
            "mesocycle",
            "create routine",
            "create program",
            "new program",
            "make program",
            "design program",
            "build program",
        ]
        
        input_lower = input_text.lower()
        for keyword in keywords:
            if keyword in input_lower:
                logger.debug(f"Matched generate_program keyword: {keyword}")
                return True
        
        return False
    
    def _check_update_routine_rules(self, input_text: str, context: Dict) -> bool:
        """Check if input matches update_routine rules.
        
        Args:
            input_text: User input text.
            context: Additional context.
            
        Returns:
            True if rules match.
        """
        # Rule 2: Update/modify keywords
        keywords = [
            "update",
            "modify",
            "tweak",
            "change",
            "adjust",
            "progress last routine",
            "make harder",
            "make easier",
            "swap exercise",
            "replace exercise",
        ]
        
        input_lower = input_text.lower()
        for keyword in keywords:
            if keyword in input_lower:
                logger.debug(f"Matched update_routine keyword: {keyword}")
                return True
        
        # Check for exercise-specific deltas
        exercise_delta_patterns = [
            r"increase.*weight",
            r"decrease.*weight",
            r"add.*reps",
            r"reduce.*reps",
            r"more.*sets",
            r"fewer.*sets",
        ]
        
        for pattern in exercise_delta_patterns:
            if re.search(pattern, input_lower):
                logger.debug(f"Matched update_routine pattern: {pattern}")
                return True
        
        return False
    
    def _calculate_score(self, input_text: str, context: Dict, prompt_key: str) -> float:
        """Calculate relevance score for a prompt.
        
        Args:
            input_text: User input text.
            context: Additional context.
            prompt_key: Prompt key to score.
            
        Returns:
            Score between 0 and 1.
        """
        input_lower = input_text.lower()
        score = 0.0
        
        # Score based on keywords and patterns
        if prompt_key == "generate_program":
            if any(kw in input_lower for kw in ["program", "routine", "generate", "create"]):
                score += 0.3
            if any(kw in input_lower for kw in ["1rm", "percentage", "%"]):
                score += 0.2
            if "schedule" in input_lower or "date" in input_lower:
                score += 0.2
        
        elif prompt_key == "update_routine":
            if any(kw in input_lower for kw in ["update", "modify", "change"]):
                score += 0.3
            if any(kw in input_lower for kw in ["exercise", "workout"]):
                score += 0.2
            if any(kw in input_lower for kw in ["harder", "easier", "weight", "reps"]):
                score += 0.2
        
        elif prompt_key == "chat_response":
            # Default fallback has baseline score
            score += 0.1
            if "?" in input_text:
                score += 0.2
            if any(kw in input_lower for kw in ["what", "how", "why", "when", "help"]):
                score += 0.2
        
        return min(score, 1.0)
    
    def route(
        self,
        input_text: str,
        context: Optional[Dict] = None,
    ) -> Tuple[str, Dict[str, float]]:
        """Route input to the appropriate prompt.
        
        Args:
            input_text: User input text.
            context: Optional additional context (user data, etc.).
            
        Returns:
            Tuple of (selected_prompt_key, scores_dict).
        """
        context = context or {}
        
        # Evaluate rules in order
        
        # Rule 1: Check for generate_program intent
        if self._check_generate_program_rules(input_text, context):
            if "generate_program" in self.available_prompts:
                logger.info("Routed to: generate_program (rule match)")
                return "generate_program", {"generate_program": 1.0}
        
        # Rule 2: Check for update_routine intent
        if self._check_update_routine_rules(input_text, context):
            if "update_routine" in self.available_prompts:
                logger.info("Routed to: update_routine (rule match)")
                return "update_routine", {"update_routine": 1.0}
        
        # Rule 3: Fallback to scoring
        scores = {}
        
        # Only score the default three prompts for now
        for prompt_key in self.DEFAULT_PROMPTS:
            if prompt_key in self.available_prompts:
                scores[prompt_key] = self._calculate_score(input_text, context, prompt_key)
        
        # Select highest score
        if scores:
            selected = max(scores, key=scores.get)
            logger.info(f"Routed to: {selected} (score: {scores[selected]:.2f})")
            return selected, scores
        
        # Ultimate fallback: chat_response
        logger.info("Routed to: chat_response (fallback)")
        return "chat_response", {"chat_response": 0.0}
    
    def route_with_tools_preference(
        self,
        input_text: str,
        context: Optional[Dict] = None,
    ) -> Tuple[str, Dict[str, float]]:
        """Route with preference for tool-using prompts when data is referenced.
        
        This implements the scoring fallback rule: prefer prompts that require tools
        when input clearly references performance data, percentages, 1RM, or dates.
        
        Args:
            input_text: User input text.
            context: Optional additional context.
            
        Returns:
            Tuple of (selected_prompt_key, scores_dict).
        """
        # First try rule-based routing
        selected, scores = self.route(input_text, context)
        
        # Check if input references data that would benefit from tools
        input_lower = input_text.lower()
        data_keywords = [
            "1rm",
            "one rep max",
            "percentage",
            "%",
            "performance",
            "records",
            "last workout",
            "progress",
            "schedule",
            "date",
        ]
        
        has_data_reference = any(kw in input_lower for kw in data_keywords)
        
        if has_data_reference:
            # Boost scores for tool-using prompts
            if "generate_program" in scores:
                scores["generate_program"] += 0.3
            if "update_routine" in scores:
                scores["update_routine"] += 0.3
            
            # Re-select based on updated scores
            if scores:
                selected = max(scores, key=scores.get)
                logger.info(f"Re-routed with tools preference to: {selected} (score: {scores[selected]:.2f})")
        
        return selected, scores


# Singleton instance
_router: Optional[ActionRouter] = None


def get_router(available_prompts: Optional[List[str]] = None) -> ActionRouter:
    """Get the singleton router instance.
    
    Args:
        available_prompts: Optional list of available prompts.
        
    Returns:
        ActionRouter instance.
    """
    global _router
    if _router is None:
        _router = ActionRouter(available_prompts=available_prompts)
    return _router


def route_input(input_text: str, context: Optional[Dict] = None) -> Tuple[str, Dict[str, float]]:
    """Route an input to the appropriate prompt (convenience function).
    
    Args:
        input_text: User input text.
        context: Optional context.
        
    Returns:
        Tuple of (selected_prompt_key, scores_dict).
    """
    router = get_router()
    return router.route_with_tools_preference(input_text, context)

