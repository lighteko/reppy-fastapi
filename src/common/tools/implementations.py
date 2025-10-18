"""LangChain StructuredTool wrappers for retriever and domain tools."""

from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field

from langchain_core.tools import StructuredTool
from loguru import logger

from src.infra.express_client import ExpressAPIClient
from src.common.tools.retriever import QdrantRetriever


# Tool Input Schemas

class RetrieverToolInput(BaseModel):
    """Input for retriever tool."""
    query: str = Field(description="The natural language query to search for")
    k: int = Field(default=5, ge=1, le=20, description="Number of results to return")


class CalculateOneRepMaxInput(BaseModel):
    """Input for calculate 1RM tool."""
    exercise_code: str = Field(description="The exercise code (e.g., 'BARBELL_BENCH_PRESS')")


class GetExerciseDetailsInput(BaseModel):
    """Input for get exercise details tool."""
    exercise_code: str = Field(description="The exercise code to look up")


class GetExercisePerformanceInput(BaseModel):
    """Input for get exercise performance records tool."""
    exercise_code: str = Field(description="The exercise code to look up")


class RecallUserMemoryInput(BaseModel):
    """Input for recall user memory tool."""
    query: str = Field(description="Natural language question about what to look for in memory")


class FindRelevantExercisesInput(BaseModel):
    """Input for find relevant exercises tool."""
    query: str = Field(description="The user's natural language query about exercises")


class GetActiveRoutinesInput(BaseModel):
    """Input for get active routines tool."""
    # No parameters needed - uses user context


# Tool Functions

class ReppyTools:
    """Factory for creating LangChain tools with injected dependencies."""
    
    def __init__(
        self,
        express_client: ExpressAPIClient,
        retriever: Optional[QdrantRetriever] = None,
        user_id: Optional[str] = None,
    ):
        """Initialize tools with dependencies.
        
        Args:
            express_client: Express API client for domain tools.
            retriever: Optional retriever for RAG tools.
            user_id: Optional user ID for context-aware tools.
        """
        self.express_client = express_client
        self.retriever = retriever
        self.user_id = user_id
    
    def create_retriever_tool(self) -> StructuredTool:
        """Create the retriever tool for semantic search."""
        if self.retriever is None:
            raise ValueError("Retriever must be provided to create retriever tool")
        
        async def retriever_func(query: str, k: int = 5) -> str:
            """Search for relevant exercises using semantic search.
            
            Args:
                query: Natural language query.
                k: Number of results to return.
                
            Returns:
                Formatted string of search results.
            """
            try:
                documents = await self.retriever.retrieve_exercises(query=query, k=k)
                
                if not documents:
                    return "No relevant exercises found."
                
                result_lines = [f"Found {len(documents)} relevant exercises:\n"]
                for i, doc in enumerate(documents, 1):
                    score = doc.metadata.get("score", 0.0)
                    exercise_code = doc.metadata.get("exercise_code", "UNKNOWN")
                    result_lines.append(
                        f"{i}. {doc.page_content} (code: {exercise_code}, score: {score:.3f})"
                    )
                
                return "\n".join(result_lines)
                
            except Exception as e:
                logger.error(f"Retriever tool error: {e}")
                return f"Error searching exercises: {str(e)}"
        
        return StructuredTool(
            name="retrieverTool",
            description="Search for relevant exercises using semantic search. Use this when you need to find exercises based on natural language queries.",
            func=retriever_func,
            coroutine=retriever_func,
            args_schema=RetrieverToolInput,
        )
    
    def create_calculate_one_rep_max_tool(self) -> StructuredTool:
        """Create tool for calculating 1RM."""
        
        async def calculate_1rm(exercise_code: str) -> str:
            """Calculate estimated one-rep max for an exercise.
            
            Args:
                exercise_code: Exercise code (e.g., 'BARBELL_BENCH_PRESS').
                
            Returns:
                Formatted string with 1RM estimate.
            """
            if not self.user_id:
                return "Error: User context not available."
            
            try:
                result = await self.express_client.calculate_one_rep_max(
                    user_id=self.user_id,
                    exercise_code=exercise_code,
                )
                
                estimated_1rm = result.get("estimated_1rm", 0)
                unit = result.get("unit", "kg")
                
                return f"Estimated 1RM for {exercise_code}: {estimated_1rm} {unit}"
                
            except Exception as e:
                logger.error(f"Calculate 1RM error: {e}")
                return f"Error calculating 1RM: {str(e)}"
        
        return StructuredTool(
            name="calculate_one_rep_max",
            description="Calculates a user's estimated one-rep max (1RM) for a specific exercise based on their recent workout history. Use this when you need to program weights based on a percentage of the user's maximum strength.",
            func=calculate_1rm,
            coroutine=calculate_1rm,
            args_schema=CalculateOneRepMaxInput,
        )
    
    def create_get_exercise_details_tool(self) -> StructuredTool:
        """Create tool for getting exercise details."""
        
        async def get_details(exercise_code: str) -> str:
            """Get detailed information for an exercise.
            
            Args:
                exercise_code: Exercise code to look up.
                
            Returns:
                Formatted string with exercise details.
            """
            try:
                result = await self.express_client.get_exercise_details(exercise_code)
                
                name = result.get("name", exercise_code)
                main_muscle = result.get("main_muscle", "N/A")
                equipment = result.get("equipment", "N/A")
                instructions = result.get("instructions", "No instructions available")
                
                return f"Exercise: {name}\nMain Muscle: {main_muscle}\nEquipment: {equipment}\nInstructions: {instructions}"
                
            except Exception as e:
                logger.error(f"Get exercise details error: {e}")
                return f"Error getting exercise details: {str(e)}"
        
        return StructuredTool(
            name="get_exercise_details",
            description="Retrieves detailed information for a single exercise, including primary and secondary muscles, detailed instructions, and safety cues. Use this if you need more context before recommending an exercise.",
            func=get_details,
            coroutine=get_details,
            args_schema=GetExerciseDetailsInput,
        )
    
    def create_get_exercise_performance_records_tool(self) -> StructuredTool:
        """Create tool for getting performance records."""
        
        async def get_performance(exercise_code: str) -> str:
            """Get performance records for an exercise.
            
            Args:
                exercise_code: Exercise code to look up.
                
            Returns:
                Formatted string with performance records.
            """
            if not self.user_id:
                return "Error: User context not available."
            
            try:
                records = await self.express_client.get_exercise_performance_records(
                    user_id=self.user_id,
                    exercise_code=exercise_code,
                )
                
                if not records:
                    return f"No performance records found for {exercise_code}."
                
                result_lines = [f"Performance records for {exercise_code}:\n"]
                for i, record in enumerate(records[:10], 1):
                    date = record.get("date", "N/A")
                    reps = record.get("actual_reps", "N/A")
                    weight = record.get("actual_weight", "N/A")
                    result_lines.append(f"{i}. {date}: {reps} reps @ {weight} kg")
                
                return "\n".join(result_lines)
                
            except Exception as e:
                logger.error(f"Get performance records error: {e}")
                return f"Error getting performance records: {str(e)}"
        
        return StructuredTool(
            name="get_exercise_performance_records",
            description="Retrieves detailed performance records for a single exercise, including the user's actual reps, weight, and rest time from past workouts. Use this to apply progressive overload based on demonstrated performance.",
            func=get_performance,
            coroutine=get_performance,
            args_schema=GetExercisePerformanceInput,
        )
    
    def create_recall_user_memory_tool(self) -> StructuredTool:
        """Create tool for recalling user memory."""
        
        async def recall_memory(query: str) -> str:
            """Search user's long-term memory.
            
            Args:
                query: Natural language query about memory.
                
            Returns:
                Formatted string with relevant memories.
            """
            if not self.user_id:
                return "Error: User context not available."
            
            try:
                memories = await self.express_client.recall_user_memory(
                    user_id=self.user_id,
                    query=query,
                )
                
                if not memories:
                    return "No relevant memories found."
                
                result_lines = [f"Found {len(memories)} relevant memories:\n"]
                for i, memory in enumerate(memories, 1):
                    content = memory.get("content", "")
                    memory_type = memory.get("memory_type", "general")
                    result_lines.append(f"{i}. [{memory_type}] {content}")
                
                return "\n".join(result_lines)
                
            except Exception as e:
                logger.error(f"Recall memory error: {e}")
                return f"Error recalling memory: {str(e)}"
        
        return StructuredTool(
            name="recall_user_memory",
            description="Searches the user's long-term memory for relevant facts, goals, or preferences that might be related to the current conversation. Use this to provide personalized and context-aware responses.",
            func=recall_memory,
            coroutine=recall_memory,
            args_schema=RecallUserMemoryInput,
        )
    
    def create_find_relevant_exercises_tool(self) -> StructuredTool:
        """Create tool for finding relevant exercises."""
        
        async def find_exercises(query: str) -> str:
            """Find exercises matching a semantic query.
            
            Args:
                query: Natural language query about exercises.
                
            Returns:
                Formatted string with relevant exercises.
            """
            try:
                exercises = await self.express_client.find_relevant_exercises(
                    query=query,
                    user_id=self.user_id,
                )
                
                if not exercises:
                    return "No relevant exercises found."
                
                result_lines = [f"Found {len(exercises)} relevant exercises:\n"]
                for i, exercise in enumerate(exercises, 1):
                    name = exercise.get("name", "Unknown")
                    code = exercise.get("code", "N/A")
                    muscle = exercise.get("main_muscle", "N/A")
                    result_lines.append(f"{i}. {name} (code: {code}, muscle: {muscle})")
                
                return "\n".join(result_lines)
                
            except Exception as e:
                logger.error(f"Find exercises error: {e}")
                return f"Error finding exercises: {str(e)}"
        
        return StructuredTool(
            name="find_relevant_exercises",
            description="Performs a semantic search to find exercises related to the user's query. Use this if the user is asking for new exercise suggestions, alternatives, or general information about a type of exercise.",
            func=find_exercises,
            coroutine=find_exercises,
            args_schema=FindRelevantExercisesInput,
        )
    
    def create_get_active_routines_tool(self) -> StructuredTool:
        """Create tool for getting active routines."""
        
        async def get_routines() -> str:
            """Get user's currently active workout routines.
            
            Returns:
                Formatted string with active routines.
            """
            if not self.user_id:
                return "Error: User context not available."
            
            try:
                routines = await self.express_client.get_active_routines(self.user_id)
                
                if not routines:
                    return "No active routines found."
                
                result_lines = [f"Found {len(routines)} active routines:\n"]
                for i, routine in enumerate(routines, 1):
                    name = routine.get("routine_name", "Unnamed")
                    plans_count = len(routine.get("plans", []))
                    result_lines.append(f"{i}. {name} ({plans_count} exercises)")
                
                return "\n".join(result_lines)
                
            except Exception as e:
                logger.error(f"Get active routines error: {e}")
                return f"Error getting active routines: {str(e)}"
        
        return StructuredTool(
            name="get_active_routines",
            description="Retrieves the user's currently active workout program, including all routines, plans, and sets. Use this when the user asks a specific question about their plan.",
            func=get_routines,
            coroutine=get_routines,
            args_schema=GetActiveRoutinesInput,
        )
    
    def get_tools_for_prompt(self, prompt_data: Dict[str, Any]) -> List[StructuredTool]:
        """Get the appropriate tools for a given prompt.
        
        Args:
            prompt_data: The loaded prompt YAML data.
            
        Returns:
            List of StructuredTool instances.
        """
        prompt_type = prompt_data.get("prompt_type", "")
        tool_specs = prompt_data.get("tools", [])
        
        tools = []
        tool_names = [spec.get("name") for spec in tool_specs]
        
        # Map tool names to factory methods
        tool_map = {
            "retrieverTool": self.create_retriever_tool,
            "calculate_one_rep_max": self.create_calculate_one_rep_max_tool,
            "get_exercise_details": self.create_get_exercise_details_tool,
            "get_exercise_performance_records": self.create_get_exercise_performance_records_tool,
            "recall_user_memory": self.create_recall_user_memory_tool,
            "find_relevant_exercises": self.create_find_relevant_exercises_tool,
            "get_active_routines": self.create_get_active_routines_tool,
        }
        
        for tool_name in tool_names:
            if tool_name in tool_map:
                try:
                    tool = tool_map[tool_name]()
                    tools.append(tool)
                except Exception as e:
                    logger.warning(f"Failed to create tool {tool_name}: {e}")
        
        logger.info(f"Created {len(tools)} tools for prompt type: {prompt_type}")
        return tools

