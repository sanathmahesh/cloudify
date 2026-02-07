"""
Base Agent class for all migration agents.

Provides common functionality for event-driven architecture and Claude AI integration.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

import anthropic
from anthropic import Anthropic


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
    - Event-driven communication
    - Claude AI integration
    - Logging and error handling
    - State management
    """

    def __init__(
        self,
        name: str,
        event_bus: EventBus,
        config: Dict[str, Any],
        claude_api_key: str,
    ):
        """
        Initialize base agent.

        Args:
            name: Agent name
            event_bus: Event bus for communication
            config: Agent configuration
            claude_api_key: Anthropic Claude API key
        """
        self.name = name
        self.event_bus = event_bus
        self.config = config
        self.status = AgentStatus.IDLE
        self.logger = logging.getLogger(f"Agent.{name}")

        # Initialize Claude client
        self.claude = Anthropic(api_key=claude_api_key)

        # Agent state
        self.state: Dict[str, Any] = {}
        self.result: Optional[AgentResult] = None

    async def execute(self) -> AgentResult:
        """
        Execute the agent.

        Returns:
            AgentResult with execution status and data
        """
        start_time = asyncio.get_event_loop().time()
        self.status = AgentStatus.RUNNING

        # Publish start event
        await self.event_bus.publish(Event(
            event_type=EventType.AGENT_STARTED,
            source_agent=self.name,
            data={"agent": self.name}
        ))

        try:
            self.logger.info(f"Starting {self.name}")

            # Execute agent-specific logic
            result = await self._execute_impl()

            # Calculate execution time
            execution_time = asyncio.get_event_loop().time() - start_time
            result.execution_time = execution_time

            # Update status
            self.status = result.status
            self.result = result

            # Publish completion event
            event_type = (
                EventType.AGENT_COMPLETED
                if result.status == AgentStatus.SUCCESS
                else EventType.AGENT_FAILED
            )

            await self.event_bus.publish(Event(
                event_type=event_type,
                source_agent=self.name,
                data={
                    "agent": self.name,
                    "status": result.status.value,
                    "data": result.data,
                    "execution_time": execution_time,
                }
            ))

            self.logger.info(
                f"Completed {self.name} - Status: {result.status.value} "
                f"({execution_time:.2f}s)"
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

            # Publish failure event
            await self.event_bus.publish(Event(
                event_type=EventType.AGENT_FAILED,
                source_agent=self.name,
                data={
                    "agent": self.name,
                    "error": str(e),
                    "execution_time": execution_time,
                }
            ))

            return result

    @abstractmethod
    async def _execute_impl(self) -> AgentResult:
        """
        Implement agent-specific execution logic.

        Returns:
            AgentResult with execution status and data
        """
        pass

    async def ask_claude(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> str:
        """
        Ask Claude AI for analysis or decision-making.

        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            max_tokens: Maximum tokens in response
            temperature: Temperature for response generation

        Returns:
            Claude's response as string
        """
        try:
            model = self.config.get("ai", {}).get("model", "claude-opus-4-6")

            kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            self.logger.debug(f"Asking Claude: {prompt[:100]}...")

            response = self.claude.messages.create(**kwargs)

            # Extract text from response
            text = response.content[0].text if response.content else ""

            self.logger.debug(f"Claude response: {text[:100]}...")

            return text

        except Exception as e:
            self.logger.error(f"Error asking Claude: {str(e)}")
            raise

    def update_state(self, key: str, value: Any) -> None:
        """Update agent state."""
        self.state[key] = value
        self.logger.debug(f"State updated: {key} = {value}")

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get value from agent state."""
        return self.state.get(key, default)
