"""Load and validate migration_config.yaml into typed dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


@dataclass
class GCPConfig:
    project_id: str
    region: str
    zone: str = "us-central1-a"
    billing_account: str = ""


@dataclass
class SourceConfig:
    root_path: str
    backend_path: str = "backend"
    frontend_path: str = "frontend"

    @property
    def backend_abs(self) -> Path:
        return Path(self.root_path).resolve() / self.backend_path

    @property
    def frontend_abs(self) -> Path:
        return Path(self.root_path).resolve() / self.frontend_path


@dataclass
class BackendConfig:
    service_name: str = "backend-api"
    port: int = 8080
    memory: str = "512Mi"
    cpu: str = "1"
    min_instances: int = 0
    max_instances: int = 3
    concurrency: int = 80
    env_vars: Dict[str, str] = field(default_factory=dict)
    jvm_opts: str = "-Xmx384m -Xms128m"
    java_version: str = "17"


@dataclass
class FrontendConfig:
    site_name: str = ""
    build_command: str = "npm run build"
    build_output: str = "build"
    node_version: str = "18"
    env_vars: Dict[str, str] = field(default_factory=dict)


@dataclass
class CloudSQLConfig:
    instance_name: str = "app-db"
    tier: str = "db-f1-micro"
    database_name: str = "appdb"
    database_version: str = "POSTGRES_15"


@dataclass
class DatabaseConfig:
    migration_strategy: str = "keep_h2"
    cloudsql: CloudSQLConfig = field(default_factory=CloudSQLConfig)


@dataclass
class AgentConfig:
    model: str = "anthropic/claude-opus-4-6"
    max_retries: int = 3
    timeout: int = 300
    verbose: bool = True


@dataclass
class ExecutionConfig:
    mode: str = "automated"
    parallel_deployments: bool = True
    generate_report: bool = True
    cleanup_on_failure: bool = True


@dataclass
class MigrationConfig:
    gcp: GCPConfig
    source: SourceConfig
    backend: BackendConfig = field(default_factory=BackendConfig)
    frontend: FrontendConfig = field(default_factory=FrontendConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    agents: AgentConfig = field(default_factory=AgentConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)


def _build(cls: type, data: Dict[str, Any]) -> Any:
    """Recursively instantiate nested dataclasses from a dict."""
    if data is None:
        return cls()
    field_types = {f.name: f.type for f in cls.__dataclass_fields__.values()}
    kwargs: Dict[str, Any] = {}
    for key, value in data.items():
        if key in field_types:
            ft = field_types[key]
            # Resolve string annotations to actual types within this module
            if isinstance(ft, str):
                ft = globals().get(ft, ft)
            if isinstance(ft, type) and hasattr(ft, "__dataclass_fields__") and isinstance(value, dict):
                kwargs[key] = _build(ft, value)
            else:
                kwargs[key] = value
    return cls(**kwargs)


def load_config(path: str | Path) -> MigrationConfig:
    """Load a YAML config file and return a validated MigrationConfig."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path) as f:
        raw: Dict[str, Any] = yaml.safe_load(f)

    gcp = _build(GCPConfig, raw.get("gcp", {}))
    source = _build(SourceConfig, raw.get("source", {}))
    backend = _build(BackendConfig, raw.get("backend", {}))
    frontend = _build(FrontendConfig, raw.get("frontend", {}))
    database = _build(DatabaseConfig, raw.get("database", {}))
    agents = _build(AgentConfig, raw.get("agents", {}))
    execution = _build(ExecutionConfig, raw.get("execution", {}))

    return MigrationConfig(
        gcp=gcp,
        source=source,
        backend=backend,
        frontend=frontend,
        database=database,
        agents=agents,
        execution=execution,
    )
