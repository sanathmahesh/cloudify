#!/usr/bin/env python3
"""
Cloudify - Automated Cloud Migration System

Main CLI entry point for the migration orchestrator.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.tree import Tree

from agents.base_agent import Event, EventBus, EventType
from agents.orchestrator import OrchestratorAgent
from utils import FileOperations, setup_logging

# Load environment variables
load_dotenv()

# Initialize Rich console
console = Console()

# Initialize Typer app
app = typer.Typer(
    name="cloudify",
    help="Automated cloud migration system for Spring Boot + React apps to GCP",
    add_completion=False,
)


class MigrationProgress:
    """Track and display migration progress."""

    def __init__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
        )
        self.tasks = {}

    def add_agent(self, agent_name: str) -> int:
        """Add agent to progress tracker."""
        task_id = self.progress.add_task(
            f"[cyan]{agent_name}...", total=100, completed=0
        )
        self.tasks[agent_name] = task_id
        return task_id

    def update_agent(self, agent_name: str, status: str, percentage: float):
        """Update agent progress."""
        if agent_name in self.tasks:
            task_id = self.tasks[agent_name]
            description = f"[green]✓[/green] {agent_name}" if status == "completed" else f"[cyan]{agent_name}"
            if status == "failed":
                description = f"[red]✗[/red] {agent_name}"

            self.progress.update(task_id, completed=percentage, description=description)


def print_banner():
    """Print application banner."""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ██████╗██╗      ██████╗ ██╗   ██╗██████╗ ██╗███████╗   ║
║  ██╔════╝██║     ██╔═══██╗██║   ██║██╔══██╗██║██╔════╝   ║
║  ██║     ██║     ██║   ██║██║   ██║██║  ██║██║█████╗     ║
║  ██║     ██║     ██║   ██║██║   ██║██║  ██║██║██╔══╝     ║
║  ╚██████╗███████╗╚██████╔╝╚██████╔╝██████╔╝██║██║        ║
║   ╚═════╝╚══════╝ ╚═════╝  ╚═════╝ ╚═════╝ ╚═╝╚═╝        ║
║                                                           ║
║        Automated Cloud Migration to Google Cloud         ║
║                   Powered by Dedalus AI                  ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""
    console.print(banner, style="bold cyan")


def validate_config(config_path: Path) -> bool:
    """Validate migration configuration."""
    if not config_path.exists():
        console.print(f"[red]Error:[/red] Configuration file not found: {config_path}")
        return False

    file_ops = FileOperations()
    config = file_ops.read_yaml(config_path)

    if not config:
        console.print(f"[red]Error:[/red] Invalid configuration file")
        return False

    # Check required fields
    required_fields = ["source", "gcp", "migration"]
    missing_fields = [field for field in required_fields if field not in config]

    if missing_fields:
        console.print(
            f"[red]Error:[/red] Missing required configuration fields: {', '.join(missing_fields)}"
        )
        return False

    # Check GCP project ID
    if not config.get("gcp", {}).get("project_id"):
        console.print("[red]Error:[/red] GCP project_id not specified in configuration")
        return False

    return True


def check_prerequisites() -> tuple[bool, list[str]]:
    """Check if all prerequisites are met."""
    errors = []

    # Check environment variables
    if not os.getenv("ANTHROPIC_API_KEY"):
        errors.append("ANTHROPIC_API_KEY environment variable not set")

    # Check for gcloud CLI
    if os.system("gcloud --version > /dev/null 2>&1") != 0:
        errors.append("gcloud CLI not installed")

    # Check for Docker
    if os.system("docker --version > /dev/null 2>&1") != 0:
        errors.append("Docker not installed")

    # Check for Firebase CLI
    if os.system("firebase --version > /dev/null 2>&1") != 0:
        errors.append("Firebase CLI not installed (optional, but recommended)")

    return len(errors) == 0, errors


async def run_migration(config_path: Path, dry_run: bool = False):
    """Run the migration process."""
    file_ops = FileOperations()
    config = file_ops.read_yaml(config_path)

    if not config:
        console.print("[red]Failed to load configuration[/red]")
        return

    # Override dry_run if specified
    if dry_run:
        config["migration"]["dry_run"] = True

    # Get API keys
    claude_api_key = os.getenv("ANTHROPIC_API_KEY")

    if not claude_api_key:
        console.print("[red]Error:[/red] ANTHROPIC_API_KEY not found in environment")
        return

    # Create event bus
    event_bus = EventBus()

    # Set up progress tracking
    migration_progress = MigrationProgress()

    # Add agents to progress tracker
    agents = [
        "CodeAnalyzer",
        "Infrastructure",
        "DatabaseMigration",
        "BackendDeployment",
        "FrontendDeployment",
    ]

    for agent in agents:
        migration_progress.add_agent(agent)

    # Subscribe to progress events
    def on_agent_completed(event: Event):
        agent_name = event.data.get("agent")
        migration_progress.update_agent(agent_name, "completed", 100)

    def on_agent_failed(event: Event):
        agent_name = event.data.get("agent")
        migration_progress.update_agent(agent_name, "failed", 100)

    def on_progress_update(event: Event):
        percentage = event.data.get("percentage", 0)
        # Update overall progress display

    event_bus.subscribe(EventType.AGENT_COMPLETED, on_agent_completed)
    event_bus.subscribe(EventType.AGENT_FAILED, on_agent_failed)
    event_bus.subscribe(EventType.PROGRESS_UPDATE, on_progress_update)

    # Create orchestrator
    orchestrator = OrchestratorAgent(
        event_bus=event_bus,
        config=config,
        claude_api_key=claude_api_key,
    )

    # Run migration with progress display
    console.print("\n[bold green]Starting migration...[/bold green]\n")

    with Live(migration_progress.progress, console=console, refresh_per_second=4):
        result = await orchestrator.execute()

    # Display results
    console.print("\n")

    if result.status.value == "success":
        console.print(
            Panel(
                "[bold green]Migration completed successfully! ✓[/bold green]",
                style="green",
            )
        )

        # Display summary
        display_summary(result.data)

    else:
        console.print(
            Panel(
                "[bold red]Migration failed ✗[/bold red]",
                style="red",
            )
        )

        if result.errors:
            console.print("\n[bold red]Errors:[/bold red]")
            for error in result.errors:
                console.print(f"  • {error}")

    if result.warnings:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for warning in result.warnings:
            console.print(f"  • {warning}")


def display_summary(data: dict):
    """Display migration summary."""
    summary = data.get("summary", {})

    # Create summary table
    table = Table(title="Migration Summary", show_header=True, header_style="bold magenta")
    table.add_column("Phase", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Time", style="yellow")

    for phase in summary.get("phases", []):
        status_icon = "✓" if phase["status"] == "success" else "✗"
        status_color = "green" if phase["status"] == "success" else "red"
        table.add_row(
            phase["agent"],
            f"[{status_color}]{status_icon} {phase['status']}[/{status_color}]",
            phase["execution_time"],
        )

    console.print("\n")
    console.print(table)

    # Display URLs
    if "backend_url" in summary or "frontend_url" in summary:
        console.print("\n[bold cyan]Deployment URLs:[/bold cyan]")

        if "backend_url" in summary:
            console.print(f"  • Backend API:  {summary['backend_url']}")

        if "frontend_url" in summary:
            console.print(f"  • Frontend App: {summary['frontend_url']}")

    console.print("\n")


@app.command()
def migrate(
    source_path: Path = typer.Option(
        "/Users/aritraraychaudhuri/Downloads/BasicApp",
        "--source-path",
        "-s",
        help="Path to source application directory",
    ),
    config_file: Path = typer.Option(
        "./migration_config.yaml",
        "--config",
        "-c",
        help="Path to migration configuration file",
    ),
    gcp_project: Optional[str] = typer.Option(
        None,
        "--gcp-project",
        "-p",
        help="GCP project ID (overrides config)",
    ),
    region: str = typer.Option(
        "us-central1",
        "--region",
        "-r",
        help="GCP region",
    ),
    mode: str = typer.Option(
        "interactive",
        "--mode",
        "-m",
        help="Execution mode: interactive or automated",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-d",
        help="Preview changes without executing",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
):
    """
    Migrate a Spring Boot + React application to Google Cloud Platform.

    This command orchestrates the complete migration process using AI agents.
    """
    print_banner()

    # Set up logging
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(level=log_level)

    # Check prerequisites
    console.print("[cyan]Checking prerequisites...[/cyan]")
    prereqs_ok, errors = check_prerequisites()

    if not prereqs_ok:
        console.print("\n[bold red]Prerequisites check failed:[/bold red]")
        for error in errors:
            console.print(f"  • {error}")
        console.print("\nPlease install missing dependencies and try again.")
        raise typer.Exit(code=1)

    console.print("[green]✓ Prerequisites check passed[/green]\n")

    # Validate configuration
    console.print("[cyan]Validating configuration...[/cyan]")

    if not validate_config(config_file):
        raise typer.Exit(code=1)

    console.print("[green]✓ Configuration valid[/green]\n")

    # Update config with CLI arguments
    file_ops = FileOperations()
    config = file_ops.read_yaml(config_file)

    if gcp_project:
        config["gcp"]["project_id"] = gcp_project

    if region:
        config["gcp"]["region"] = region

    config["source"]["path"] = str(source_path.resolve())
    config["migration"]["mode"] = mode

    # Confirm with user in interactive mode
    if mode == "interactive" and not dry_run:
        console.print("[bold yellow]Migration Configuration:[/bold yellow]")
        console.print(f"  Source: {source_path}")
        console.print(f"  GCP Project: {config['gcp']['project_id']}")
        console.print(f"  Region: {config['gcp']['region']}")
        console.print(f"  Mode: {mode}")
        console.print()

        confirm = typer.confirm("Proceed with migration?")
        if not confirm:
            console.print("Migration cancelled.")
            raise typer.Exit(code=0)

    # Run migration
    asyncio.run(run_migration(config_file, dry_run))


@app.command()
def init():
    """
    Initialize a new migration configuration file.

    Creates a template migration_config.yaml in the current directory.
    """
    console.print("[cyan]Initializing migration configuration...[/cyan]")

    config_file = Path("migration_config.yaml")

    if config_file.exists():
        overwrite = typer.confirm(
            f"{config_file} already exists. Overwrite?"
        )
        if not overwrite:
            console.print("Cancelled.")
            raise typer.Exit(code=0)

    # Copy template
    template_path = Path(__file__).parent / "migration_config.yaml"

    if template_path.exists():
        import shutil
        shutil.copy(template_path, config_file)
        console.print(f"[green]✓ Created {config_file}[/green]")
        console.print("\nEdit the configuration file and run:")
        console.print("  [cyan]python migration_orchestrator.py migrate[/cyan]")
    else:
        console.print("[red]Error:[/red] Template configuration not found")
        raise typer.Exit(code=1)


@app.command()
def version():
    """Show version information."""
    console.print("[bold cyan]Cloudify[/bold cyan] v1.0.0")
    console.print("Automated Cloud Migration System")
    console.print("\nPowered by:")
    console.print("  • Dedalus AI")
    console.print("  • Claude API")
    console.print("  • Google Cloud Platform")


if __name__ == "__main__":
    app()
