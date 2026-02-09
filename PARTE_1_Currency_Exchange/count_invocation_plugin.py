# PLUGIN - COUNTS AGENT INVOCATIONS AND MODEL CALLS

import logging

from google.genai import types
from typing import Optional, Any

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.adk.plugins.base_plugin import BasePlugin


# Applies to all agent and model calls
class CountInvocationPlugin(BasePlugin):
    """A custom plugin that counts agent and tool invocations."""

    def __init__(self) -> None:
        """Initialize the plugin with counters."""
        super().__init__(name="count_invocation")
        self.agent_count: int = 0
        self.tool_count: int = 0
        self.llm_request_count: int = 0

    # Callback 1: Runs before an agent is called. You can add any custom logic here.
    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> None:
        """Count agent runs."""
        self.agent_count += 1
        self._log(f"[Plugin] Agent run count: {self.agent_count}")

    # Callback 2: Runs before a model is called. You can add any custom logic here.
    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> None:
        """Count LLM requests."""
        self.llm_request_count += 1
        self._log(f"[Plugin] LLM request count: {self.llm_request_count}")

    async def after_model_callback(
      self, *, callback_context: CallbackContext, llm_response: LlmResponse
    ) -> Optional[LlmResponse]:
        """Log LLM response after receiving from model."""
        self._log(f"[Plugin] LLM response received: {self._format_content(llm_response.content)}")
        return llm_response

    async def before_tool_callback(
      self,
      *,
      tool: BaseTool,
      tool_args: dict[str, Any],
      tool_context: ToolContext,
    ) -> Optional[dict]:
        """Count Tool requests."""
        self.tool_count += 1
        self._log(f"[Plugin] Tool count: {self.tool_count}")
        
        """Log tool execution start."""
        self._log(f"🔧 TOOL STARTING")
        self._log(f"   Tool Name: {tool.name}")
        self._log(f"   Agent: {tool_context.agent_name}")
        self._log(f"   Function Call ID: {tool_context.function_call_id}")
        self._log(f"   Arguments: {self._format_args(tool_args)}\n")
        return None

    async def after_tool_callback(
      self,
      *,
      tool: BaseTool,
      tool_args: dict[str, Any],
      tool_context: ToolContext,
      result: dict,
    ) -> Optional[dict]:
        
        """Log tool execution completion."""
        self._log(f"🔧 TOOL COMPLETED")
        self._log(f"   Tool Name: {tool.name}")
        self._log(f"   Agent: {tool_context.agent_name}")
        self._log(f"   Function Call ID: {tool_context.function_call_id}")
        self._log(f"   Result: {self._format_args(result)}\n----------\n")
        return None

        
    def _log(self, message: str) -> None:
        """Internal method to format and print log messages."""
        # ANSI color codes: \033[90m for grey, \033[0m to reset
        formatted_message: str = f"\033[90m[{self.name}] {message}\033[0m"
        print(formatted_message)
        
    def _format_content(
        self, content: Optional[types.Content], max_length: int = 200
    ) -> str:
        """Format content for logging, truncating if too long."""
        if not content or not content.parts:
            return "None"

        parts = []
        for part in content.parts:
            if part.text:
                text = part.text.strip()
                if len(text) > max_length:
                    text = text[:max_length] + "..."
                    parts.append(f"text: '{text}'")
            elif part.function_call:
                parts.append(f"function_call: {part.function_call.name}")
            elif part.function_response:
                parts.append(f"function_response: {part.function_response.name}")
            elif part.code_execution_result:
                parts.append("code_execution_result")
            else:
                parts.append("other_part")

            return " | ".join(parts)

    def _format_args(self, args: dict[str, Any], max_length: int = 300) -> str:
        """Format arguments dictionary for logging."""
        if not args:
            return "{}"
        formatted = str(args)
        if len(formatted) > max_length:
            formatted = formatted[:max_length] + "...}"
        return formatted