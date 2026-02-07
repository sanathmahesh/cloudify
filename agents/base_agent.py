"""
Base Agent class for all migration agents.

Provides common functionality for event-driven architecture and Dedalus AI integration
with multi-model handoffs and tool calling.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from dedalus_labs import AsyncDedalus
from dedalus_labs.lib.runner import DedalusRunner


# ---------------------------------------------------------------------------
# Model registry — optimal models per task type (key for hackathon judging)
# ---------------------------------------------------------------------------

class ModelRole(Enum):
    """Semantic roles for model selection – each maps to the best provider."""
    REASONING = "openai/gpt-4.1"            # Best for deep analysis & reasoning
    CODE_GENERATION = "anthropic/claude-opus-4-6"  # Best for code generation
    PLANNING = "anthropic/claude-sonnet-4-5-20250514"  # Great for planning & creative
    FAST = "openai/gpt-4.1-mini"            # Fast & cheap for simple tasks
    MULTI_MODEL = [                          # Let Dedalus route between models
        "openai/gpt-4.1",
        "anthropic/claude-opus-4-6",
    ]


class AgentStatus(Enum):
    """Agent execution status."""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class EventType(Enum):
    """Event types for agent communication."""
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    ANALYSIS_COMPLETE = "analysis_complete"
    INFRASTRUCTURE_READY = "infrastructure_ready"
    DATABASE_MIGRATED = "database_migrated"
    BACKEND_DEPLOYED = "backend_deployed"
    FRONTEND_DEPLOYED = "frontend_deployed"
    MIGRATION_COMPLETE = "migration_complete"
    ERROR_OCCURRED = "error_occurred"
    PROGRESS_UPDATE = "progress_update"
    # New: track model handoffs for demo visibility
    MODEL_HANDOFF = "model_handoff"
    TOOL_INVOKED = "tool_invoked"


@dataclass
class Event:
    """Event for agent communication."""
    event_type: EventType
    source_agent: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class AgentResult:
    """Result of agent execution."""
    status: AgentStatus
    data: Dict[str, Any]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    # New: track which models and tools were used (great for demo)
    models_used: List[str] = field(default_factory=list)
    tools_called: List[str] = field(default_factory=list)


class EventBus:
    """
    Event bus for agent communication.

    Implements pub-sub pattern for decoupled agent communication.
    """

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._event_history: List[Event] = []
        self.logger = logging.getLogger(self.__class__.__name__)

    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """Subscribe to an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        self.logger.debug(f"Subscribed to {event_type.value}")

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        self._event_history.append(event)
        self.logger.info(
            f"Event published: {event.event_type.value} from {event.source_agent}"
        )

        if event.event_type in self._subscribers:
            for callback in self._subscribers[event.event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    self.logger.error(f"Error in event callback: {str(e)}")

    def get_history(self, event_type: Optional[EventType] = None) -> List[Event]:
        """Get event history, optionally filtered by type."""
        if event_type:
            return [e for e in self._event_history if e.event_type == event_type]
        return self._event_history


class BaseAgent(ABC):
    """
    Base class for all migration agents.

    Provides common functionality:
    - Event-driven communication via EventBus
    - Dedalus SDK integration with DedalusRunner for multi-model handoffs
    - Tool calling via typed Python functions
    - MCP server connectivity
    - Logging and error handling
    - State management
    """

    def __init__(
        self,
        name: str,
        event_bus: EventBus,
        config: Dict[str, Any],
        dedalus_api_key: str,
    ):
        self.name = name
        self.event_bus = event_bus
        self.config = config
        self.status = AgentStatus.IDLE
        self.logger = logging.getLogger(f"Agent.{name}")

        # Initialize Dedalus client & runner (replaces raw Anthropic client)
        self.dedalus_client = AsyncDedalus(api_key=dedalus_api_key)
        self.runner = DedalusRunner(self.dedalus_client)

        # Agent state
        self.state: Dict[str, Any] = {}
        self.result: Optional[AgentResult] = None

        # Track models and tools used (for demo dashboard)
        self._models_used: List[str] = []
        self._tools_called: List[str] = []

    async def _invoke_tool(self, tool_fn: Callable, *args, **kwargs) -> Any:
        """Call a tool function directly and track it for the Dedalus SDK usage summary.

        Use this instead of calling tool functions directly so that every
        tool invocation is recorded in _tools_called and published as a
        TOOL_INVOKED event for the real-time dashboard.
        """
        tool_name = tool_fn.__name__
        self._tools_called.append(tool_name)
        self.logger.info(f"[{self.name}] Tool invoked: {tool_name}")

        # Publish event for real-time tracking
        try:
            await self.event_bus.publish(Event(
                event_type=EventType.TOOL_INVOKED,
                source_agent=self.name,
                data={"tool": tool_name},
            ))
        except Exception:
            pass

        return await tool_fn(*args, **kwargs)

    def _on_tool_event(self, event: Any) -> None:
        """Callback fired when the DedalusRunner invokes a tool.

        Publishes a TOOL_INVOKED event for real-time dashboard tracking.
        """
        tool_name = getattr(event, "tool_name", str(event))
        self._tools_called.append(tool_name)
        self.logger.info(f"[{self.name}] Tool invoked: {tool_name}")
        # Fire-and-forget event publish (non-blocking)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.event_bus.publish(Event(
                event_type=EventType.TOOL_INVOKED,
                source_agent=self.name,
                data={"tool": tool_name},
            )))
        except RuntimeError:
            pass  # No running loop – skip event

    async def execute(self) -> AgentResult:
        """Execute the agent."""
        start_time = asyncio.get_event_loop().time()
        self.status = AgentStatus.RUNNING

        await self.event_bus.publish(Event(
            event_type=EventType.AGENT_STARTED,
            source_agent=self.name,
            data={"agent": self.name},
        ))

        try:
            self.logger.info(f"Starting {self.name}")
            result = await self._execute_impl()

            execution_time = asyncio.get_event_loop().time() - start_time
            result.execution_time = execution_time
            result.models_used = self._models_used
            result.tools_called = self._tools_called

            self.status = result.status
            self.result = result

            event_type = (
                EventType.AGENT_COMPLETED
                if result.status == AgentStatus.SUCCESS
                else EventType.AGENT_FAILED
            )

            event_data = {
                    "agent": self.name,
                    "status": result.status.value,
                    "data": result.data,
                    "execution_time": execution_time,
                    "models_used": result.models_used,
                    "tools_called": result.tools_called,
            }
            if result.errors:
                event_data["error"] = "; ".join(result.errors)

            await self.event_bus.publish(Event(
                event_type=event_type,
                source_agent=self.name,
                data=event_data,
            ))

            self.logger.info(
                f"Completed {self.name} - Status: {result.status.value} "
                f"({execution_time:.2f}s) | Models: {result.models_used} | Tools: {result.tools_called}"
            )

            return result

        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            self.logger.error(f"Error in {self.name}: {str(e)}", exc_info=True)

            result = AgentResult(
                status=AgentStatus.FAILED,
                data={},
                errors=[str(e)],
                execution_time=execution_time,
            )

            self.status = AgentStatus.FAILED
            self.result = result

            await self.event_bus.publish(Event(
                event_type=EventType.AGENT_FAILED,
                source_agent=self.name,
                data={
                    "agent": self.name,
                    "error": str(e),
                    "execution_time": execution_time,
                },
            ))

            return result

    @abstractmethod
    async def _execute_impl(self) -> AgentResult:
        """Implement agent-specific execution logic."""
        pass

    async def run_with_dedalus(
        self,
        prompt: str,
        model: str | list[str] | None = None,
        tools: list | None = None,
        mcp_servers: list[str] | None = None,
        instructions: str | None = None,
        max_steps: int = 10,
        policy: Any | None = None,
    ) -> str:
        """
        Run a task using the DedalusRunner with model handoffs and tool calling.

        This replaces the old ask_claude() method. It supports:
        - Multi-model handoffs via model list
        - Local tool calling via typed functions
        - MCP server integration
        - Policy-based dynamic model routing
        - on_tool_event callbacks for real-time tracking

        Args:
            prompt: The user prompt / task description.
            model: Model ID or list of models for handoff routing.
            tools: List of callable tool functions.
            mcp_servers: List of MCP server slugs/URLs.
            instructions: System instructions for the agent.
            max_steps: Max agentic loop iterations.
            policy: Optional policy function for dynamic routing.

        Returns:
            The final text output from the runner.
        """
        # Default model from config
        if model is None:
            model = self.config.get("ai", {}).get("model", "anthropic/claude-opus-4-6")

        # Track which model(s) we're using
        if isinstance(model, list):
            self._models_used.extend(model)
        else:
            self._models_used.append(model)

        # Publish model handoff event (for demo visibility)
        await self.event_bus.publish(Event(
            event_type=EventType.MODEL_HANDOFF,
            source_agent=self.name,
            data={"model": model, "prompt_preview": prompt[:100]},
        ))

        kwargs: Dict[str, Any] = {
            "input": prompt,
            "model": model,
            "max_steps": max_steps,
            "on_tool_event": self._on_tool_event,
        }

        if tools:
            kwargs["tools"] = tools
        if mcp_servers:
            kwargs["mcp_servers"] = mcp_servers
        if instructions:
            kwargs["instructions"] = instructions
        if policy:
            kwargs["policy"] = policy

        temperature = self.config.get("ai", {}).get("temperature", 0.3)
        kwargs["temperature"] = temperature

        self.logger.debug(f"DedalusRunner.run() with model={model}, tools={[t.__name__ for t in (tools or [])]}")

        result = await self.runner.run(**kwargs)

        # Track tools called from the RunResult
        if hasattr(result, "tools_called") and result.tools_called:
            self._tools_called.extend(result.tools_called)

        return result.final_output

    def update_state(self, key: str, value: Any) -> None:
        """Update agent state."""
        self.state[key] = value
        self.logger.debug(f"State updated: {key} = {value}")

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get value from agent state."""
        return self.state.get(key, default)
