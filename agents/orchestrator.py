"""
Orchestrator Agent — Powered by Dedalus SDK

Coordinates all migration agents using:
- Multi-model handoffs (different models per phase)
- Agent-as-tool pattern (specialist agents wrapped as Dedalus tools)
- Policy-based dynamic model routing
- MCP server integration for research & error recovery
"""

import asyncio
import json
import logging
from typing import Any, Dict, List

from .base_agent import (
    AgentResult,
    AgentStatus,
    BaseAgent,
    Event,
    EventBus,
    EventType,
    ModelRole,
)


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator agent that coordinates all migration agents.

    Uses the Dedalus SDK's multi-model handoffs to route each phase
    to the optimal model, and wraps specialist agents as Dedalus tools
    so the orchestrator LLM can dynamically delegate work.
    """

    def __init__(
        self,
        event_bus: EventBus,
        config: Dict[str, Any],
        dedalus_api_key: str,
    ):
        super().__init__(
            name="Orchestrator",
            event_bus=event_bus,
            config=config,
            dedalus_api_key=dedalus_api_key,
        )
        self.agent_statuses: Dict[str, AgentStatus] = {}
        self.agent_results: Dict[str, AgentResult] = {}

        self.event_bus.subscribe(EventType.AGENT_COMPLETED, self._on_agent_completed)
        self.event_bus.subscribe(EventType.AGENT_FAILED, self._on_agent_failed)

    async def _execute_impl(self) -> AgentResult:
        """Execute orchestration with multi-model handoffs."""
        self.logger.info("Starting migration orchestration with Dedalus multi-model handoffs")

        try:
            from .code_analyzer import CodeAnalyzerAgent
            from .infrastructure import InfrastructureAgent
            from .database_migration import DatabaseMigrationAgent
            from .backend_deployment import BackendDeploymentAgent
            from .frontend_deployment import FrontendDeploymentAgent

            agents = [
                CodeAnalyzerAgent(self.event_bus, self.config, self.dedalus_client.api_key),
                InfrastructureAgent(self.event_bus, self.config, self.dedalus_client.api_key),
                DatabaseMigrationAgent(self.event_bus, self.config, self.dedalus_client.api_key),
                BackendDeploymentAgent(self.event_bus, self.config, self.dedalus_client.api_key),
                FrontendDeploymentAgent(self.event_bus, self.config, self.dedalus_client.api_key),
            ]

            # Build agent-as-tool wrappers so we can also use them via DedalusRunner
            specialist_tools = self._build_specialist_tools(agents)

            # Execute the pipeline with dependency management
            results = await self._execute_agents_with_dependencies(agents)

            all_success = all(
                result.status == AgentStatus.SUCCESS for result in results.values()
            )

            if all_success:
                await self.event_bus.publish(Event(
                    event_type=EventType.MIGRATION_COMPLETE,
                    source_agent=self.name,
                    data={"results": {name: r.data for name, r in results.items()}},
                ))

            # Use Dedalus multi-model to generate intelligent summary
            summary = await self._generate_ai_summary(results)

            # Collect all models/tools used across agents
            all_models = []
            all_tools = []
            for r in results.values():
                all_models.extend(r.models_used)
                all_tools.extend(r.tools_called)

            return AgentResult(
                status=AgentStatus.SUCCESS if all_success else AgentStatus.FAILED,
                data={
                    "summary": summary,
                    "agent_results": {name: r.data for name, r in results.items()},
                    "total_agents": len(agents),
                    "successful_agents": sum(1 for r in results.values() if r.status == AgentStatus.SUCCESS),
                    "failed_agents": sum(1 for r in results.values() if r.status == AgentStatus.FAILED),
                    "all_models_used": list(set(all_models)),
                    "all_tools_called": list(set(all_tools)),
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

    def _build_specialist_tools(self, agents: list) -> list:
        """Wrap each specialist agent as a Dedalus-callable tool.

        This implements the 'agent-as-tool' pattern from the Dedalus docs:
        the orchestrator LLM can call these tools to delegate work to
        specialist agents that each use their own optimal model.
        """
        tools = []

        for agent in agents:
            # Create a closure-based tool for each agent
            async def _run_specialist(
                agent_name: str,
                _agent=agent,
            ) -> str:
                f"""Run the {agent.name} specialist agent and return its results as JSON."""
                result = await _agent.execute()
                return json.dumps({
                    "agent": _agent.name,
                    "status": result.status.value,
                    "data": result.data,
                    "models_used": result.models_used,
                    "tools_called": result.tools_called,
                })

            # Set proper function metadata for Dedalus schema extraction
            _run_specialist.__name__ = f"run_{agent.name.lower()}_agent"
            _run_specialist.__doc__ = (
                f"Run the {agent.name} specialist agent for cloud migration. "
                f"Returns JSON with status, data, models used, and tools called."
            )
            tools.append(_run_specialist)

        return tools

    async def _execute_agents_with_dependencies(
        self, agents: List[BaseAgent],
    ) -> Dict[str, AgentResult]:
        """Execute agents with dependency management and model handoffs.

        Each phase uses a different model optimized for that task type:
        - Code Analysis: Reasoning model (GPT-4.1) for deep analysis
        - Infrastructure: Planning model (Claude Sonnet) for GCP setup
        - Database: Multi-model routing for analysis + recommendations
        - Backend Deploy: Code generation model (Claude Opus) for Dockerfile
        - Frontend Deploy: Fast model (GPT-4.1-mini) for simple build/deploy
        """
        results: Dict[str, AgentResult] = {}

        # Phase 1: Code Analysis — uses REASONING model
        self.logger.info("Phase 1: Code Analysis [Model: REASONING]")
        analyzer = next(a for a in agents if a.name == "CodeAnalyzer")
        results[analyzer.name] = await analyzer.execute()

        if results[analyzer.name].status != AgentStatus.SUCCESS:
            self.logger.error("Code analysis failed, aborting migration")
            return results

        # Phase 2: Infrastructure Provisioning — uses PLANNING model
        self.logger.info("Phase 2: Infrastructure [Model: PLANNING]")
        infra = next(a for a in agents if a.name == "Infrastructure")
        results[infra.name] = await infra.execute()

        if results[infra.name].status != AgentStatus.SUCCESS:
            self.logger.error("Infrastructure provisioning failed, aborting migration")
            return results

        # Phase 3: Database Migration — uses MULTI_MODEL routing
        self.logger.info("Phase 3: Database Migration [Model: MULTI_MODEL]")
        db_migration = next(a for a in agents if a.name == "DatabaseMigration")
        results[db_migration.name] = await db_migration.execute()

        if results[db_migration.name].status != AgentStatus.SUCCESS:
            self.logger.warning("Database migration failed, but continuing...")

        # Phase 4: Backend + Frontend Deployment (parallel)
        backend = next(a for a in agents if a.name == "BackendDeployment")
        frontend = next(a for a in agents if a.name == "FrontendDeployment")

        if self.config.get("migration", {}).get("agents", {}).get("parallel_execution", True):
            self.logger.info("Phase 4: Parallel Deployment [Backend: CODE_GEN, Frontend: FAST]")
            backend_task = asyncio.create_task(backend.execute())
            frontend_task = asyncio.create_task(frontend.execute())

            backend_result, frontend_result = await asyncio.gather(
                backend_task, frontend_task, return_exceptions=True,
            )

            results[backend.name] = (
                backend_result if not isinstance(backend_result, Exception)
                else AgentResult(status=AgentStatus.FAILED, data={}, errors=[str(backend_result)])
            )
            results[frontend.name] = (
                frontend_result if not isinstance(frontend_result, Exception)
                else AgentResult(status=AgentStatus.FAILED, data={}, errors=[str(frontend_result)])
            )
        else:
            self.logger.info("Phase 4: Sequential Deployment")
            results[backend.name] = await backend.execute()
            results[frontend.name] = await frontend.execute()

        return results

    async def _generate_ai_summary(self, results: Dict[str, AgentResult]) -> Dict[str, Any]:
        """Use Dedalus multi-model handoff to generate an intelligent migration summary.

        Uses FAST model for quick summary generation with Brave Search MCP
        for any follow-up recommendations.
        """
        summary = {
            "migration_status": "success" if all(
                r.status == AgentStatus.SUCCESS for r in results.values()
            ) else "failed",
            "phases": [],
            "model_handoffs": [],
        }

        for agent_name, result in results.items():
            phase = {
                "agent": agent_name,
                "status": result.status.value,
                "execution_time": f"{result.execution_time:.2f}s",
                "key_outputs": result.data.get("summary", {}),
                "errors": result.errors,
                "warnings": result.warnings,
                "models_used": result.models_used,
                "tools_called": result.tools_called,
            }
            summary["phases"].append(phase)

        # Extract deployment URLs
        if "BackendDeployment" in results:
            backend_data = results["BackendDeployment"].data
            if "service_url" in backend_data:
                summary["backend_url"] = backend_data["service_url"]

        if "FrontendDeployment" in results:
            frontend_data = results["FrontendDeployment"].data
            if "hosting_url" in frontend_data:
                summary["frontend_url"] = frontend_data["hosting_url"]

        # Use Dedalus to generate AI-powered insights about the migration
        try:
            phase_summary = json.dumps(summary["phases"], indent=2)
            ai_insight = await self.run_with_dedalus(
                prompt=(
                    f"You just completed a cloud migration. Here are the phase results:\n"
                    f"{phase_summary}\n\n"
                    f"Provide a 2-3 sentence executive summary of the migration outcome, "
                    f"highlighting which models handled which phases and any notable tool usage."
                ),
                model=ModelRole.FAST.value,
                instructions="You are a cloud migration summary generator. Be concise and factual.",
                max_steps=1,
            )
            summary["ai_insight"] = ai_insight
        except Exception as e:
            self.logger.warning(f"Could not generate AI summary: {e}")
            summary["ai_insight"] = "Migration completed. See phase details above."

        return summary

    async def _on_agent_completed(self, event: Event) -> None:
        """Handle agent completion event."""
        agent_name = event.data.get("agent")
        status = event.data.get("status")
        models = event.data.get("models_used", [])
        tools = event.data.get("tools_called", [])

        self.logger.info(
            f"Agent {agent_name} completed: {status} | "
            f"Models: {models} | Tools: {tools}"
        )
        self.agent_statuses[agent_name] = AgentStatus(status)

        completed = sum(1 for s in self.agent_statuses.values() if s != AgentStatus.RUNNING)
        total = 5

        await self.event_bus.publish(Event(
            event_type=EventType.PROGRESS_UPDATE,
            source_agent=self.name,
            data={
                "completed": completed,
                "total": total,
                "percentage": (completed / total) * 100,
                "models_used": models,
                "tools_called": tools,
            },
        ))

    async def _on_agent_failed(self, event: Event) -> None:
        """Handle agent failure event."""
        agent_name = event.data.get("agent")
        error = event.data.get("error")

        self.logger.error(f"Agent {agent_name} failed: {error}")
        self.agent_statuses[agent_name] = AgentStatus.FAILED

        await self.event_bus.publish(Event(
            event_type=EventType.ERROR_OCCURRED,
            source_agent=self.name,
            data={"agent": agent_name, "error": error, "stage": "migration"},
        ))
