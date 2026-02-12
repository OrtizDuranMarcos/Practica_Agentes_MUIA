# PLUGIN - OBSERVABILITY AND DEBUGGING FOR U-QAM AGENT

import logging
from typing import Optional, Any
from google.genai import types

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.adk.plugins.base_plugin import BasePlugin

class UQAMDebugPlugin(BasePlugin):
    """
    A custom plugin focused on observability during agent execution.
    It provides clear visual separators and detailed logs for tools and agent interactions.
    """

    def __init__(self) -> None:
        super().__init__(name="uqam_debug_plugin")
        self.step_count = 0

    def _log(self, message: str, color: str = "\033[97m") -> None:
        """Internal method to format and print log messages with color."""
        # ANSI color codes for better visibility
        # 97m = White, 94m = Blue, 92m = Green, 93m = Yellow, 90m = Grey
        print(f"{color}{message}\033[0m")

    def _header(self, title: str) -> None:
        print(f"\n\033[1;36m{'='*60}\n {title}\n{'='*60}\033[0m")

    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> None:
        self.step_count += 1
        self._header(f"STEP {self.step_count}: AGENT START ({agent.name})")

    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> None:
        self._log(f"[LLM Request] Model: {llm_request.model}", "\033[95m") # Purple
        # prompt_preview = str(llm_request.messages)[:200] + "..." if len(str(llm_request.messages)) > 200 else str(llm_request.messages)
        # self._log(f"   Context/Prompt Preview: {prompt_preview}", "\033[90m") # Grey

    async def after_model_callback(
        self, *, callback_context: CallbackContext, llm_response: LlmResponse
    ) -> Optional[LlmResponse]:
        self._log(f"[LLM Response] Received response", "\033[95m")
        return llm_response

    async def before_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
    ) -> Optional[dict]:
        self._log(f"\n[TOOL CALL] {tool.name}", "\033[1;33m") # Bold Yellow
        self._log(f"   Arguments: {tool_args}", "\033[33m")
        return None

    async def after_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        result: dict,
    ) -> Optional[dict]:
        self._log(f"[TOOL RESULT] {tool.name}", "\033[1;32m") # Bold Green
        # Format result nicely
        result_str = str(result)
        if len(result_str) > 500:
             result_str = result_str[:500] + "... [TRUNCATED]"
        self._log(f"   Output: {result_str}", "\033[32m")
        return None
