"""Generate migration summary reports."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from utils.state import MigrationState, AgentStatus

console = Console()


def generate_report(state: MigrationState, output_dir: str = ".") -> str:
    """Generate a migration summary report and write it to disk."""
    report: Dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "pipeline": state.pipeline.to_dict(),
        "deployment_urls": state.deployment_urls,
        "generated_files": state.generated_files,
        "artifacts": {
            k: v for k, v in state.artifacts.items()
            if isinstance(v, (str, int, float, bool, list, dict))
        },
    }

    out_path = Path(output_dir) / "migration_report.json"
    out_path.write_text(json.dumps(report, indent=2))
    return str(out_path)


def print_summary(state: MigrationState) -> None:
    """Print a rich summary table to the terminal."""
    table = Table(title="Migration Summary", show_lines=True)
    table.add_column("Agent", style="bold")
    table.add_column("Status")
    table.add_column("Duration (s)")
    table.add_column("Details")

    status_styles = {
        AgentStatus.COMPLETED: "[green]COMPLETED[/green]",
        AgentStatus.FAILED: "[red]FAILED[/red]",
        AgentStatus.RUNNING: "[yellow]RUNNING[/yellow]",
        AgentStatus.PENDING: "[dim]PENDING[/dim]",
        AgentStatus.SKIPPED: "[dim]SKIPPED[/dim]",
        AgentStatus.ROLLED_BACK: "[red]ROLLED BACK[/red]",
    }

    for name, agent in state.pipeline.agents.items():
        style = status_styles.get(agent.status, str(agent.status.value))
        duration = str(agent.duration) if agent.duration else "-"
        detail = agent.error or ", ".join(
            f"{k}={v}" for k, v in list(agent.output.items())[:3]
        ) or "-"
        table.add_row(name, style, duration, detail[:80])

    console.print(table)

    if state.deployment_urls:
        url_text = "\n".join(f"  {k}: {v}" for k, v in state.deployment_urls.items())
        console.print(Panel(url_text, title="Deployment URLs", border_style="green"))

    total = state.pipeline.duration
    if total:
        console.print(f"\n[bold]Total duration:[/bold] {total}s")
