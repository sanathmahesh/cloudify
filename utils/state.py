"""Pipeline state management for tracking migration progress across agents."""

from __future__ import annotations

import enum
import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


class AgentStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


@dataclass
class AgentState:
    name: str
    status: AgentStatus = AgentStatus.PENDING
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    error: Optional[str] = None
    output: Dict[str, Any] = field(default_factory=dict)
    rollback_actions: List[str] = field(default_factory=list)

    @property
    def duration(self) -> Optional[float]:
        if self.started_at and self.finished_at:
            return round(self.finished_at - self.started_at, 2)
        return None

    def mark_running(self) -> None:
        self.status = AgentStatus.RUNNING
        self.started_at = time.time()

    def mark_completed(self, output: Optional[Dict[str, Any]] = None) -> None:
        self.status = AgentStatus.COMPLETED
        self.finished_at = time.time()
        if output:
            self.output.update(output)

    def mark_failed(self, error: str) -> None:
        self.status = AgentStatus.FAILED
        self.finished_at = time.time()
        self.error = error

    def mark_rolled_back(self) -> None:
        self.status = AgentStatus.ROLLED_BACK
        self.finished_at = time.time()


@dataclass
class PipelineState:
    agents: Dict[str, AgentState] = field(default_factory=dict)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    overall_status: AgentStatus = AgentStatus.PENDING

    def register_agent(self, name: str) -> AgentState:
        state = AgentState(name=name)
        self.agents[name] = state
        return state

    def get_agent(self, name: str) -> AgentState:
        return self.agents[name]

    def start(self) -> None:
        self.started_at = time.time()
        self.overall_status = AgentStatus.RUNNING

    def finish(self, success: bool) -> None:
        self.finished_at = time.time()
        self.overall_status = AgentStatus.COMPLETED if success else AgentStatus.FAILED

    @property
    def duration(self) -> Optional[float]:
        if self.started_at and self.finished_at:
            return round(self.finished_at - self.started_at, 2)
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status.value,
            "duration_seconds": self.duration,
            "agents": {
                name: {
                    "status": a.status.value,
                    "duration_seconds": a.duration,
                    "error": a.error,
                    "output": a.output,
                }
                for name, a in self.agents.items()
            },
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))


class MigrationState:
    """Global state container shared across agents during a migration run."""

    def __init__(self) -> None:
        self.pipeline = PipelineState()
        self.artifacts: Dict[str, Any] = {}
        self.deployment_urls: Dict[str, str] = {}
        self.generated_files: List[str] = []
        self.dry_run_scripts: List[str] = []

    def set_artifact(self, key: str, value: Any) -> None:
        self.artifacts[key] = value

    def get_artifact(self, key: str, default: Any = None) -> Any:
        return self.artifacts.get(key, default)
