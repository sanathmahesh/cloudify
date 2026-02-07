"""
Orchestrator Agent

Coordinates all migration agents and manages the overall migration pipeline.
"""

import asyncio
import logging
from typing import Any, Dict, List

from .base_agent import AgentResult, AgentStatus, BaseAgent, Event, EventBus, EventType


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator agent that coordinates all migration agents.

    Responsibilities:
    - Coordinate agent execution order
    - Monitor migration pipeline status
    - Handle dependencies between agents
    - Aggregate results and generate summary
    """

    def __init__(
        self,
        event_bus: EventBus,
        config: Dict[str, Any],
        claude_api_key: str,
    ):
        super().__init__(
            name="Orchestrator",
            event_bus=event_bus,
            config=config,
            claude_api_key=claude_api_key,
        )

        # Track agent statuses
        self.agent_statuses: Dict[str, AgentStatus] = {}
        self.agent_results: Dict[str, AgentResult] = {}

        # Subscribe to agent events
        self.event_bus.subscribe(EventType.AGENT_COMPLETED, self._on_agent_completed)
        self.event_bus.subscribe(EventType.AGENT_FAILED, self._on_agent_failed)

    async def _execute_impl(self) -> AgentResult:
        """
        Execute orchestration logic.

        Returns:
            AgentResult with migration summary
        """
        self.logger.info("Starting migration orchestration")

        try:
            # Import agents here to avoid circular imports
            from .code_analyzer import CodeAnalyzerAgent
            from .infrastructure import InfrastructureAgent
            from .database_migration import DatabaseMigrationAgent
            from .backend_deployment import BackendDeploymentAgent
            from .frontend_deployment import FrontendDeploymentAgent

            # Initialize all agents
            agents = [
                CodeAnalyzerAgent(self.event_bus, self.config, self.claude.api_key),
                InfrastructureAgent(self.event_bus, self.config, self.claude.api_key),
                DatabaseMigrationAgent(self.event_bus, self.config, self.claude.api_key),
                BackendDeploymentAgent(self.event_bus, self.config, self.claude.api_key),
                FrontendDeploymentAgent(self.event_bus, self.config, self.claude.api_key),
            ]

            # Execute agents sequentially (with dependencies)
            results = await self._execute_agents_with_dependencies(agents)

            # Check if all agents succeeded
            all_success = all(
                result.status == AgentStatus.SUCCESS for result in results.values()
            )

            if all_success:
                await self.event_bus.publish(Event(
                    event_type=EventType.MIGRATION_COMPLETE,
                    source_agent=self.name,
                    data={"results": {name: r.data for name, r in results.items()}}
                ))

            # Generate summary
            summary = self._generate_summary(results)

            return AgentResult(
                status=AgentStatus.SUCCESS if all_success else AgentStatus.FAILED,
                data={
                    "summary": summary,
                    "agent_results": {name: r.data for name, r in results.items()},
                    "total_agents": len(agents),
                    "successful_agents": sum(
                        1 for r in results.values() if r.status == AgentStatus.SUCCESS
                    ),
                    "failed_agents": sum(
                        1 for r in results.values() if r.status == AgentStatus.FAILED
                    ),
                },
                errors=[
                    f"{name}: {', '.join(result.errors)}"
                    for name, result in results.items()
                    if result.errors
                ],
                warnings=[
                    f"{name}: {', '.join(result.warnings)}"
                    for name, result in results.items()
                    if result.warnings
                ],
            )

        except Exception as e:
            self.logger.error(f"Orchestration failed: {str(e)}", exc_info=True)
            return AgentResult(
                status=AgentStatus.FAILED,
                data={},
                errors=[str(e)],
            )

    async def _execute_agents_with_dependencies(
        self, agents: List[BaseAgent]
    ) -> Dict[str, AgentResult]:
        """
        Execute agents with dependency management.

        Execution order:
        1. Code Analyzer (analyzes source code)
        2. Infrastructure Provisioning (sets up GCP resources)
        3. Database Migration (migrates database if needed)
        4. Backend + Frontend Deployment (parallel execution possible)

        Args:
            agents: List of agents to execute

        Returns:
            Dictionary mapping agent name to result
        """
        results: Dict[str, AgentResult] = {}

        # Phase 1: Code Analysis
        analyzer = next(a for a in agents if a.name == "CodeAnalyzer")
        results[analyzer.name] = await analyzer.execute()

        if results[analyzer.name].status != AgentStatus.SUCCESS:
            self.logger.error("Code analysis failed, aborting migration")
            return results

        # Phase 2: Infrastructure Provisioning
        infra = next(a for a in agents if a.name == "Infrastructure")
        results[infra.name] = await infra.execute()

        if results[infra.name].status != AgentStatus.SUCCESS:
            self.logger.error("Infrastructure provisioning failed, aborting migration")
            return results

        # Phase 3: Database Migration
        db_migration = next(a for a in agents if a.name == "DatabaseMigration")
        results[db_migration.name] = await db_migration.execute()

        if results[db_migration.name].status != AgentStatus.SUCCESS:
            self.logger.warning("Database migration failed, but continuing...")

        # Phase 4: Backend and Frontend Deployment (parallel)
        backend = next(a for a in agents if a.name == "BackendDeployment")
        frontend = next(a for a in agents if a.name == "FrontendDeployment")

        # Check if parallel execution is enabled
        if self.config.get("migration", {}).get("agents", {}).get("parallel_execution", True):
            self.logger.info("Executing backend and frontend deployment in parallel")

            backend_task = asyncio.create_task(backend.execute())
            frontend_task = asyncio.create_task(frontend.execute())

            backend_result, frontend_result = await asyncio.gather(
                backend_task, frontend_task, return_exceptions=True
            )

            if isinstance(backend_result, Exception):
                results[backend.name] = AgentResult(
                    status=AgentStatus.FAILED,
                    data={},
                    errors=[str(backend_result)],
                )
            else:
                results[backend.name] = backend_result

            if isinstance(frontend_result, Exception):
                results[frontend.name] = AgentResult(
                    status=AgentStatus.FAILED,
                    data={},
                    errors=[str(frontend_result)],
                )
            else:
                results[frontend.name] = frontend_result
        else:
            # Sequential execution
            self.logger.info("Executing backend deployment")
            results[backend.name] = await backend.execute()

            self.logger.info("Executing frontend deployment")
            results[frontend.name] = await frontend.execute()

        return results

    def _generate_summary(self, results: Dict[str, AgentResult]) -> Dict[str, Any]:
        """
        Generate migration summary.

        Args:
            results: Dictionary mapping agent name to result

        Returns:
            Summary dictionary
        """
        summary = {
            "migration_status": "success" if all(
                r.status == AgentStatus.SUCCESS for r in results.values()
            ) else "failed",
            "phases": [],
        }

        for agent_name, result in results.items():
            phase = {
                "agent": agent_name,
                "status": result.status.value,
                "execution_time": f"{result.execution_time:.2f}s",
                "key_outputs": result.data.get("summary", {}),
                "errors": result.errors,
                "warnings": result.warnings,
            }
            summary["phases"].append(phase)

        # Extract deployment URLs if available
        if "BackendDeployment" in results:
            backend_data = results["BackendDeployment"].data
            if "service_url" in backend_data:
                summary["backend_url"] = backend_data["service_url"]

        if "FrontendDeployment" in results:
            frontend_data = results["FrontendDeployment"].data
            if "hosting_url" in frontend_data:
                summary["frontend_url"] = frontend_data["hosting_url"]

        return summary

    async def _on_agent_completed(self, event: Event) -> None:
        """Handle agent completion event."""
        agent_name = event.data.get("agent")
        status = event.data.get("status")

        self.logger.info(f"Agent {agent_name} completed with status: {status}")
        self.agent_statuses[agent_name] = AgentStatus(status)

        # Publish progress update
        completed = sum(
            1 for s in self.agent_statuses.values() if s != AgentStatus.RUNNING
        )
        total = 6  # Total number of agents (including orchestrator)

        await self.event_bus.publish(Event(
            event_type=EventType.PROGRESS_UPDATE,
            source_agent=self.name,
            data={
                "completed": completed,
                "total": total - 1,  # Exclude orchestrator
                "percentage": (completed / (total - 1)) * 100,
            }
        ))

    async def _on_agent_failed(self, event: Event) -> None:
        """Handle agent failure event."""
        agent_name = event.data.get("agent")
        error = event.data.get("error")

        self.logger.error(f"Agent {agent_name} failed: {error}")
        self.agent_statuses[agent_name] = AgentStatus.FAILED

        # Publish error event
        await self.event_bus.publish(Event(
            event_type=EventType.ERROR_OCCURRED,
            source_agent=self.name,
            data={
                "agent": agent_name,
                "error": error,
                "stage": "migration",
            }
        ))
