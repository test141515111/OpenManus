import json
from typing import Any, Dict, List, Optional, ClassVar

from app.agent.base import BaseAgent
from app.prompt.xinobi import SYSTEM_PROMPT, NEXT_STEP_PROMPT
from app.schema import AgentState, Message
from app.tool.base import BaseTool
from app.tool.collection import ToolCollection


class XinobiAgent(BaseAgent):
    """Xinobi Agent implementation.
    
    This agent implements the Xinobi specifications for an AI assistant that interacts with
    computer environments to solve tasks through real-time interaction.
    """
    
    name: str = "xinobi_agent"
    available_tools: ToolCollection = None
    llm: Any = None
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self, llm, tools: List[BaseTool] = None):
        """Initialize the Xinobi agent.
        
        Args:
            llm: The language model client to use for generating responses.
            tools (List[BaseTool], optional): List of tools available to the agent.
        """
        super().__init__()
        self.llm = llm
        
        # Initialize tools if provided
        if tools:
            self.available_tools = ToolCollection(*tools)
        
        # Initialize memory with system prompt
        self.add_message(Message.system_message(SYSTEM_PROMPT + "\n\n" + NEXT_STEP_PROMPT))
    
    async def step(self, user_input: Optional[str] = None) -> Dict[str, Any]:
        """Execute a single step of the agent's reasoning and action cycle.
        
        Args:
            user_input (Optional[str]): User input to process, if any.
            
        Returns:
            Dict[str, Any]: The result of the agent's step, including any actions to be taken.
        """
        # Add user input to memory if provided
        if user_input:
            self.add_message(Message.user_message(user_input))
        
        # Check for stuck state
        if self.is_stuck():
            self.handle_stuck_state()
        
        # Get messages for LLM
        messages = self.memory.to_dict_list()
        
        # Prepare parameters for LLM
        params = {
            "messages": messages,
        }
        
        # Add tools if available
        if self.available_tools:
            params["tools"] = [tool.to_param() for tool in self.available_tools.tools]
        
        # Get response from LLM
        response = await self.llm.completion(**params)
        
        # Process tool calls if any
        if response.get("tool_calls"):
            tool_results = await self._execute_tools(response["tool_calls"])
            
            # Add assistant message with tool calls to memory
            assistant_message = Message.from_tool_calls(
                tool_calls=response["tool_calls"],
                content=response.get("content", "")
            )
            self.add_message(assistant_message)
            
            # Add tool results to memory
            for tool_result in tool_results:
                self.add_message(tool_result["message"])
            
            # Format response with Japanese structure
            formatted_response = self._format_japanese_response(
                response.get("content", ""),
                tool_results
            )
            
            return {
                "response": formatted_response,
                "tool_results": tool_results,
                "state": self.state
            }
        else:
            # Add assistant message to memory
            self.add_message(Message.assistant_message(response.get("content", "")))
            
            # Format response with Japanese structure
            formatted_response = self._format_japanese_response(
                response.get("content", ""),
                []
            )
            
            return {
                "response": formatted_response,
                "state": self.state
            }
    
    async def _execute_tools(self, tool_calls):
        """Execute tool calls and return results.
        
        Args:
            tool_calls: Tool calls from LLM response.
            
        Returns:
            List of tool results.
        """
        tool_results = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            
            # Check if tool exists
            if not self.available_tools or not self.available_tools.get(tool_name):
                error_msg = f"Tool '{tool_name}' not found"
                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "result": {"error": error_msg, "success": False},
                    "message": Message.tool_message(
                        content=error_msg,
                        name=tool_name,
                        tool_call_id=tool_call.id
                    )
                })
                continue
            
            # Get tool and arguments
            tool = self.available_tools.get(tool_name)
            try:
                # Parse arguments
                import json
                args = json.loads(tool_call.function.arguments)
                
                # Execute tool
                result = await tool(**args)
                
                # Create tool message
                tool_message = Message.tool_message(
                    content=str(result),
                    name=tool_name,
                    tool_call_id=tool_call.id
                )
                
                # Add result
                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "result": result,
                    "message": tool_message
                })
                
                # Check for terminate tool
                if tool_name == "terminate":
                    self.state = AgentState.FINISHED
                
            except Exception as e:
                error_msg = f"Error executing tool '{tool_name}': {str(e)}"
                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "result": {"error": error_msg, "success": False},
                    "message": Message.tool_message(
                        content=error_msg,
                        name=tool_name,
                        tool_call_id=tool_call.id
                    )
                })
        
        return tool_results
    
    def _format_japanese_response(self, content, tool_results):
        """Format response according to Japanese Xinobi format.
        
        Args:
            content: Content from LLM response.
            tool_results: Results from tool executions.
            
        Returns:
            Formatted response string.
        """
        # Extract sections from content if they exist
        sections = {
            "状況分析": "",
            "アクションプラン": [],
            "コマンド実行": "",
            "結果分析": "",
            "次のステップ": "",
            "ユーザーへの質問/確認": ""
        }
        
        # Try to extract sections from content
        current_section = "状況分析"
        lines = content.split("\n")
        
        for line in lines:
            if "【状況分析】" in line:
                current_section = "状況分析"
                continue
            elif "【アクションプラン】" in line:
                current_section = "アクションプラン"
                continue
            elif "【コマンド実行】" in line:
                current_section = "コマンド実行"
                continue
            elif "【結果分析】" in line:
                current_section = "結果分析"
                continue
            elif "【次のステップ】" in line:
                current_section = "次のステップ"
                continue
            elif "【ユーザーへの質問/確認】" in line:
                current_section = "ユーザーへの質問/確認"
                continue
            
            # Add line to current section
            if current_section == "アクションプラン" and line.strip().startswith("-"):
                sections[current_section].append(line.strip())
            elif current_section in sections:
                if isinstance(sections[current_section], list):
                    if line.strip():
                        sections[current_section].append(line.strip())
                else:
                    sections[current_section] += line + "\n"
        
        # If no structured content was found, use the entire content as situation analysis
        if not any(sections.values()):
            sections["状況分析"] = content
        
        # Add tool execution results to command execution and result analysis if not already present
        if tool_results and not sections["コマンド実行"] and not sections["結果分析"]:
            tool_commands = []
            tool_results_text = []
            
            for result in tool_results:
                tool_name = result["name"]
                if tool_name == "execute_bash":
                    args = json.loads(result["tool_call_id"].function.arguments)
                    tool_commands.append(f"$ {args.get('command', '')}")
                elif tool_name == "python_execute":
                    args = json.loads(result["tool_call_id"].function.arguments)
                    tool_commands.append(f"Python実行:\n```python\n{args.get('code', '')}\n```")
                else:
                    tool_commands.append(f"{tool_name}ツールを実行")
                
                # Add result
                result_content = str(result["result"])
                if result_content:
                    tool_results_text.append(f"{tool_name}の結果:\n{result_content}")
            
            if tool_commands:
                sections["コマンド実行"] = "\n".join(tool_commands)
            
            if tool_results_text:
                sections["結果分析"] = "\n".join(tool_results_text)
        
        # Format response using the base class method
        return self.format_response(
            content=sections["状況分析"].strip(),
            action_plan=sections["アクションプラン"] if sections["アクションプラン"] else None,
            command=sections["コマンド実行"].strip() if sections["コマンド実行"] else None,
            result_analysis=sections["結果分析"].strip() if sections["結果分析"] else None,
            next_steps=sections["次のステップ"].strip() if sections["次のステップ"] else None,
            user_questions=sections["ユーザーへの質問/確認"].strip() if sections["ユーザーへの質問/確認"] else None
        )
