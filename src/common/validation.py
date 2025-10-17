"""Pydantic validation schemas and domain guards."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
from enum import Enum


# Enums

class SetTypeCode(str, Enum):
    """Valid set type codes."""
    NORMAL = "NORMAL"
    WARMUP = "WARMUP"
    DROPSET = "DROPSET"
    SUPERSET = "SUPERSET"


# Response Schemas for Chat

class ChatResponse(BaseModel):
    """Validation schema for chat_response prompt output."""
    reply: str = Field(description="The complete natural-language response to the user's message")
    suggested_questions: Optional[List[str]] = Field(default=None, max_items=3, description="Up to 3 follow-up questions")
    tone: Optional[str] = Field(default=None, description="Single-word descriptor of tone")
    
    @validator("reply")
    def reply_not_empty(cls, v):
        """Ensure reply is not empty."""
        if not v or not v.strip():
            raise ValueError("Reply cannot be empty")
        return v


# Response Schemas for Program Generation

class SetSchema(BaseModel):
    """Schema for a single set."""
    set_type_code: Optional[str] = Field(default="NORMAL", description="Set type code")
    set_order: int = Field(ge=1, description="Set sequence order")
    reps: Optional[int] = Field(default=None, ge=1, description="Target repetitions")
    weight: Optional[float] = Field(default=None, ge=0, description="Weight in user's unit system")
    rest_time: int = Field(ge=0, description="Rest time in seconds")
    duration: Optional[int] = Field(default=None, ge=0, description="Duration in seconds for timed exercises")
    
    @validator("reps", "duration")
    def at_least_one_metric(cls, v, values):
        """Ensure either reps or duration is specified."""
        if v is None and values.get("duration") is None:
            # Allow both to be None for now, validation happens at plan level
            pass
        return v


class PlanSchema(BaseModel):
    """Schema for an exercise plan."""
    exercise_code: str = Field(description="Exercise code from available context")
    plan_order: int = Field(ge=1, description="Exercise sequence order in routine")
    notes: Optional[str] = Field(default=None, description="Optional notes for this exercise")
    sets: List[SetSchema] = Field(min_items=1, description="List of sets for this exercise")
    
    @validator("exercise_code")
    def exercise_code_not_empty(cls, v):
        """Ensure exercise code is not empty."""
        if not v or not v.strip():
            raise ValueError("Exercise code cannot be empty")
        return v.strip().upper()


class RoutineSchema(BaseModel):
    """Schema for a workout routine."""
    routine_name: str = Field(description="Descriptive name for the routine")
    routine_order: int = Field(ge=1, description="Sequence order for this routine in the cycle")
    notes: Optional[str] = Field(default=None, description="Optional overall notes for the routine")
    plans: List[PlanSchema] = Field(min_items=1, description="List of exercise plans")
    
    @validator("routine_name")
    def routine_name_not_empty(cls, v):
        """Ensure routine name is not empty."""
        if not v or not v.strip():
            raise ValueError("Routine name cannot be empty")
        return v.strip()


class GenerateProgramResponse(BaseModel):
    """Validation schema for generate_program prompt output."""
    routines: List[RoutineSchema] = Field(min_items=1, description="List of all routines in the program")
    
    @validator("routines")
    def validate_routine_orders(cls, v):
        """Ensure routine orders are sequential."""
        if not v:
            raise ValueError("At least one routine is required")
        
        orders = [r.routine_order for r in v]
        if len(set(orders)) != len(orders):
            raise ValueError("Routine orders must be unique")
        
        return v


class UpdateRoutineResponse(BaseModel):
    """Validation schema for update_routine prompt output."""
    routine_name: str = Field(description="Name of the routine")
    routine_order: int = Field(ge=1, description="Sequence order for this routine")
    notes: Optional[str] = Field(default=None, description="Optional notes")
    plans: List[PlanSchema] = Field(min_items=1, description="Updated list of exercise plans")


# Domain Guards

class DomainValidator:
    """Domain-specific validation logic."""
    
    def __init__(self, available_context: Optional[Dict[str, Any]] = None):
        """Initialize with available context.
        
        Args:
            available_context: Dict containing exercises and set_types from prompt variables.
        """
        self.available_context = available_context or {}
        self.valid_exercise_codes = set()
        self.valid_set_type_codes = set()
        
        if available_context:
            # Extract valid codes from context
            exercises = available_context.get("exercises", [])
            self.valid_exercise_codes = {ex.get("exercise_code") for ex in exercises if ex.get("exercise_code")}
            
            set_types = available_context.get("set_types", [])
            self.valid_set_type_codes = {st.get("set_type_code") for st in set_types if st.get("set_type_code")}
    
    def validate_exercise_code(self, exercise_code: str) -> bool:
        """Check if exercise code is in available context.
        
        Args:
            exercise_code: The exercise code to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        if not self.valid_exercise_codes:
            # If no context loaded, allow any code
            return True
        
        return exercise_code in self.valid_exercise_codes
    
    def validate_set_type_code(self, set_type_code: str) -> bool:
        """Check if set type code is in available context.
        
        Args:
            set_type_code: The set type code to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        if not self.valid_set_type_codes:
            # If no context loaded, allow any code
            return True
        
        return set_type_code in self.valid_set_type_codes
    
    def validate_routine(self, routine: Union[Dict[str, Any], RoutineSchema]) -> Dict[str, List[str]]:
        """Validate a routine against domain rules.
        
        Args:
            routine: The routine to validate.
            
        Returns:
            Dict with "errors" list and "warnings" list.
        """
        errors = []
        warnings = []
        
        # Convert to dict if needed
        if isinstance(routine, RoutineSchema):
            routine_dict = routine.model_dump()
        else:
            routine_dict = routine
        
        plans = routine_dict.get("plans", [])
        
        for i, plan in enumerate(plans):
            plan_idx = i + 1
            exercise_code = plan.get("exercise_code", "")
            
            # Validate exercise code
            if not self.validate_exercise_code(exercise_code):
                errors.append(f"Plan {plan_idx}: Invalid exercise code '{exercise_code}'")
            
            # Validate sets
            sets = plan.get("sets", [])
            if not sets:
                errors.append(f"Plan {plan_idx}: No sets defined")
            
            for j, set_data in enumerate(sets):
                set_idx = j + 1
                set_type_code = set_data.get("set_type_code", "NORMAL")
                
                # Validate set type
                if not self.validate_set_type_code(set_type_code):
                    errors.append(f"Plan {plan_idx}, Set {set_idx}: Invalid set type '{set_type_code}'")
                
                # Check that either reps or duration is specified
                reps = set_data.get("reps")
                duration = set_data.get("duration")
                if reps is None and duration is None:
                    warnings.append(f"Plan {plan_idx}, Set {set_idx}: Neither reps nor duration specified")
        
        return {
            "errors": errors,
            "warnings": warnings,
        }


def validate_response(
    response_data: Dict[str, Any],
    prompt_type: str,
    available_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Validate an LLM response against the appropriate schema.
    
    Args:
        response_data: The response data to validate.
        prompt_type: The type of prompt (chat_response, generate_program, update_routine).
        available_context: Optional available context for domain validation.
        
    Returns:
        Dict with "valid", "errors", "warnings", and "validated_data" keys.
    """
    errors = []
    warnings = []
    validated_data = None
    
    try:
        # Select appropriate schema
        if prompt_type == "chat_response":
            validated_data = ChatResponse(**response_data)
        elif prompt_type == "generate_program":
            validated_data = GenerateProgramResponse(**response_data)
            
            # Additional domain validation
            if available_context:
                validator = DomainValidator(available_context)
                for routine in validated_data.routines:
                    result = validator.validate_routine(routine)
                    errors.extend(result["errors"])
                    warnings.extend(result["warnings"])
        
        elif prompt_type == "update_routine":
            validated_data = UpdateRoutineResponse(**response_data)
            
            # Additional domain validation
            if available_context:
                validator = DomainValidator(available_context)
                result = validator.validate_routine(validated_data)
                errors.extend(result["errors"])
                warnings.extend(result["warnings"])
        else:
            errors.append(f"Unknown prompt type: {prompt_type}")
        
        is_valid = len(errors) == 0
        
        return {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "validated_data": validated_data.model_dump() if validated_data else None,
        }
        
    except Exception as e:
        errors.append(f"Validation error: {str(e)}")
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "validated_data": None,
        }

