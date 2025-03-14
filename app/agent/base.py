from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schema import AgentState, Memory, Message


class BaseAgent(ABC, BaseModel):
    """Base class for all agents in the Xinobi system.
    
    This abstract class defines the core functionality and interface that all agents must implement.
    It provides state management, memory tracking, and the basic execution flow.
    """
    
    name: str = "xinobi_base_agent"
    state: AgentState = AgentState.IDLE
    memory: Memory = Field(default_factory=Memory)
    duplicate_threshold: int = 1  # Lower threshold for detecting stuck states
    
    class Config:
        arbitrary_types_allowed = True
        
    @asynccontextmanager
    async def state_context(self, new_state: AgentState):
        """Context manager for safe agent state transitions.
        
        Args:
            new_state: The state to transition to during the context.
            
        Yields:
            None: Allows execution within the new state.
            
        Raises:
            ValueError: If the new_state is invalid.
        """
        if not isinstance(new_state, AgentState):
            raise ValueError(f"Invalid state: {new_state}")
            
        previous_state = self.state
        self.state = new_state
        try:
            yield
        except Exception as e:
            self.state = AgentState.ERROR  # Transition to ERROR on failure
            raise e
        finally:
            self.state = previous_state  # Revert to previous state
    
    def reset(self) -> None:
        """Reset the agent state and memory."""
        self.state = AgentState.IDLE
        self.memory = Memory()
    
    def add_message(self, message: Message) -> None:
        """Add a message to the agent's memory.
        
        Args:
            message (Message): The message to add to memory.
        """
        self.memory.add_message(message)
    
    def add_messages(self, messages: List[Message]) -> None:
        """Add multiple messages to the agent's memory.
        
        Args:
            messages (List[Message]): The messages to add to memory.
        """
        self.memory.add_messages(messages)
    
    @abstractmethod
    async def step(self, **kwargs) -> Dict[str, Any]:
        """Execute a single step of the agent's reasoning and action cycle.
        
        This method must be implemented by all agent subclasses to define their specific behavior.
        
        Returns:
            Dict[str, Any]: The result of the agent's step, including any actions to be taken.
        """
        pass
        
    async def run(self, user_input: Optional[str] = None) -> Dict[str, Any]:
        """Execute the agent's main loop asynchronously.
        
        Args:
            user_input: Optional initial user input to process.
            
        Returns:
            Dict[str, Any]: The result of the agent's execution.
            
        Raises:
            RuntimeError: If the agent is not in IDLE state at start.
        """
        if self.state != AgentState.IDLE:
            raise RuntimeError(f"Cannot run agent from state: {self.state}")
            
        # Process user input if provided
        if user_input:
            self.add_message(Message.user_message(user_input))
            
        # Execute agent step with state context management
        async with self.state_context(AgentState.RUNNING):
            try:
                result = await self.step()
                self.state = AgentState.IDLE
                return result
            except Exception as e:
                self.state = AgentState.ERROR
                raise e
                
    def is_stuck(self) -> bool:
        """Check if the agent is stuck in a loop by detecting duplicate content.
        
        Returns:
            bool: True if the agent is stuck, False otherwise.
        """
        if len(self.memory.messages) < 3:  # Need at least 3 messages for pattern detection
            return False
            
        # Get the last two assistant messages
        assistant_messages = [
            msg for msg in self.memory.messages 
            if msg.role == "assistant" and msg.content
        ]
        
        if len(assistant_messages) < 2:
            return False
            
        # Check if the last two assistant messages are identical
        last_msg = assistant_messages[-1]
        prev_msg = assistant_messages[-2]
        
        # Compare content similarity (exact match for simplicity)
        is_duplicate = last_msg.content == prev_msg.content
        
        print(f"Stuck state check: duplicate={is_duplicate}")
        
        return is_duplicate
        
    def handle_stuck_state(self):
        """Handle stuck state by adding a prompt to change strategy."""
        # Log the stuck state
        print(f"Agent detected stuck state. Adding prompt to change strategy.")
        
        # In a real implementation, you might want to add a system message
        # to the memory to guide the agent to try a different approach
        self.add_message(Message.system_message(
            "Observed duplicate responses. Consider new strategies and avoid repeating ineffective paths."
        ))
    
    def format_response(self, content: str, action_plan: Optional[List[str]] = None, 
                       command: Optional[str] = None, result_analysis: Optional[str] = None,
                       next_steps: Optional[str] = None, user_questions: Optional[str] = None) -> str:
        """Format the agent's response according to the Xinobi response format.
        
        Args:
            content (str): The situation analysis content.
            action_plan (Optional[List[str]]): List of action plan items.
            command (Optional[str]): The command being executed.
            result_analysis (Optional[str]): Analysis of command execution results.
            next_steps (Optional[str]): Description of next steps.
            user_questions (Optional[str]): Questions or confirmations for the user.
            
        Returns:
            str: Formatted response according to Xinobi specifications.
        """
        response_parts = []
        
        # Add situation analysis
        response_parts.append("【状況分析】")
        response_parts.append(content)
        
        # Add action plan if provided
        if action_plan:
            response_parts.append("\n【アクションプラン】")
            for item in action_plan:
                response_parts.append(f"- {item}")
        
        # Add command execution if provided
        if command:
            response_parts.append("\n【コマンド実行】")
            response_parts.append(command)
        
        # Add result analysis if provided
        if result_analysis:
            response_parts.append("\n【結果分析】")
            response_parts.append(result_analysis)
        
        # Add next steps if provided
        if next_steps:
            response_parts.append("\n【次のステップ】")
            response_parts.append(next_steps)
        
        # Add user questions if provided
        if user_questions:
            response_parts.append("\n【ユーザーへの質問/確認】")
            response_parts.append(user_questions)
        
        return "\n".join(response_parts)
