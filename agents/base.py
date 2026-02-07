"""Base agent class that all migration agents inherit from.

Each agent wraps a DedalusRunner call with:
- Standardized lifecycle (start → execute → complete/fail)
- State tracking via MigrationState
- Retry logic with configurable max_retries
- Rollback support
- Dry-run mode that generates scripts instead of executing
"""

from __future__ import annotations

import abc
import asyncio
import traceback
from typing import Any, Dict, List, Optional

from dedalus_labs import AsyncDedalus, DedalusRunner

from utils.config import MigrationConfig
from utils.logger import get_logger
from utils.state import AgentState, MigrationState

log = get_logger(__name__)


class BaseAgent(abc.ABC):
    """Abstract base class for all Cloudify migration agents."""

    name: str = "base"

    def __init__(
        self,
        config: MigrationConfig,
        state: MigrationState,
        dry_run: bool = False,
    ) -> None:
        self.config = config
        self.state = state
        self.dry_run = dry_run
        self.agent_state: AgentState = state.pipeline.register_agent(self.name)
        self.log = get_logger(f"agent.{self.name}")

        # Dedalus client + runner (initialized lazily)
        self._client: Optional[AsyncDedalus] = None
        self._runner: Optional[DedalusRunner] = None

    @property
    def client(self) -> AsyncDedalus:
        if self._client is None:
            self._client = AsyncDedalus()
        return self._client

    @property
    def runner(self) -> DedalusRunner:
        if self._runner is None:
            self._runner = DedalusRunner(self.client)
        return self._runner

    @property
    def model(self) -> str:
        return self.config.agents.model

    # -- Abstract methods agents must implement --------------------------------

    @abc.abstractmethod
    def get_tools(self) -> List[Any]:
        """Return the list of tool functions this agent provides to the LLM."""
        ...

    @abc.abstractmethod
    def get_prompt(self) -> str:
        """Return the system/task prompt for this agent."""
        ...

    @abc.abstractmethod
    async def execute(self) -> Dict[str, Any]:
        """Run the agent's core logic. Return a dict of output artifacts."""
        ...

    async def rollback(self) -> None:
        """Override to implement rollback logic when this agent fails."""
        self.log.info(f"No rollback actions defined for {self.name}")

    # -- Lifecycle -------------------------------------------------------------

    async def run(self) -> Dict[str, Any]:
        """Execute the agent with retry logic and state tracking."""
        max_retries = self.config.agents.max_retries
        self.agent_state.mark_running()
        self.log.info(f"[agent]>>> {self.name} agent started[/agent]")

        last_error: Optional[str] = None
        for attempt in range(1, max_retries + 1):
            try:
                output = await self.execute()
                self.agent_state.mark_completed(output)
                self.log.info(
                    f"[success]<<< {self.name} agent completed[/success] "
                    f"(attempt {attempt})"
                )
                return output
            except Exception as exc:
                last_error = f"{exc}\n{traceback.format_exc()}"
                self.log.warning(
                    f"{self.name} attempt {attempt}/{max_retries} failed: {exc}"
                )
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)

        self.agent_state.mark_failed(last_error or "Unknown error")
        self.log.error(f"[error]<<< {self.name} agent FAILED after {max_retries} attempts[/error]")
        return {}

    # -- Dedalus helper --------------------------------------------------------

    async def ask_llm(self, prompt: str, tools: Optional[List[Any]] = None) -> str:
        """Send a prompt to the LLM via DedalusRunner and return the text response."""
        result = await self.runner.run(
            input=prompt,
            model=self.model,
            tools=tools or [],
        )
        if hasattr(result, "choices") and result.choices:
            return result.choices[0].message.content or ""
        if isinstance(result, str):
            return result
        return str(result)
