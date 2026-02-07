"""
Database Migration Agent — Powered by Dedalus SDK

Handles database migration using:
- MULTI_MODEL routing (GPT-4.1 + Claude) for analysis + recommendations
- Local tools for Cloud SQL provisioning
- MCP server (Brave Search) for researching database best practices
"""

import json
from typing import Any, Dict

from .base_agent import AgentResult, AgentStatus, BaseAgent, Event, EventType, ModelRole
from .dedalus_tools import DATABASE_TOOLS, create_cloud_sql_instance, detect_database_type


class DatabaseMigrationAgent(BaseAgent):
    """
    Database Migration agent powered by Dedalus SDK.

    Uses MULTI_MODEL routing to combine reasoning (for analysis) with
    code generation (for SQL migration scripts).
    """

    def __init__(self, event_bus, config: Dict[str, Any], dedalus_api_key: str):
        super().__init__(
            name="DatabaseMigration",
            event_bus=event_bus,
            config=config,
            dedalus_api_key=dedalus_api_key,
        )

    async def _execute_impl(self) -> AgentResult:
        """Execute database migration with multi-model handoffs."""
        self.logger.info("Starting database migration with Dedalus MULTI_MODEL routing")

        analysis_events = self.event_bus.get_history(EventType.ANALYSIS_COMPLETE)
        if not analysis_events:
            return AgentResult(
                status=AgentStatus.FAILED,
                data={},
                errors=["No code analysis results available"],
            )

        analysis_data = analysis_events[-1].data
        db_info = analysis_data.get("database", {})
        db_strategy = self.config.get("gcp", {}).get("database", {}).get("strategy", "keep-h2")

        warnings: list[str] = []
        migration_result: Dict[str, Any] = {
            "strategy": db_strategy,
            "database_type": db_info.get("type", "unknown"),
            "database_mode": db_info.get("mode", "unknown"),
            "action_taken": None,
            "recommendations": [],
        }

        try:
            if db_strategy == "keep-h2":
                self.logger.info("Keeping H2 database configuration")
                result = self._keep_h2_strategy(db_info)
                migration_result.update(result)
                warnings.extend(result.get("warnings", []))

            elif db_strategy == "migrate-to-cloud-sql":
                self.logger.info("Migrating to Cloud SQL")
                result = await self._migrate_to_cloud_sql(db_info)
                migration_result.update(result)
                if not result.get("success"):
                    return AgentResult(
                        status=AgentStatus.FAILED,
                        data=migration_result,
                        errors=result.get("errors", []),
                    )
            else:
                return AgentResult(
                    status=AgentStatus.FAILED,
                    data={},
                    errors=[f"Unknown database strategy: {db_strategy}"],
                )

            # Use Dedalus MULTI_MODEL for AI recommendations
            ai_recs = await self._get_ai_recommendations(db_info, db_strategy)
            migration_result["recommendations"].extend(ai_recs)

            await self.event_bus.publish(Event(
                event_type=EventType.DATABASE_MIGRATED,
                source_agent=self.name,
                data=migration_result,
            ))

            return AgentResult(
                status=AgentStatus.SUCCESS,
                data=migration_result,
                warnings=warnings,
            )

        except Exception as e:
            self.logger.error(f"Database migration error: {str(e)}", exc_info=True)
            return AgentResult(
                status=AgentStatus.FAILED,
                data=migration_result,
                errors=[str(e)],
            )

    def _keep_h2_strategy(self, db_info: Dict[str, Any]) -> Dict[str, Any]:
        """Keep H2 database with appropriate warnings."""
        result: Dict[str, Any] = {"action_taken": "kept_h2", "warnings": [], "recommendations": []}
        db_mode = db_info.get("mode", "unknown")

        if db_mode == "in-memory":
            result["warnings"].extend([
                "H2 in-memory database will lose all data when Cloud Run instance restarts",
                "Cloud Run instances can restart at any time, leading to data loss",
                "Strongly recommend migrating to Cloud SQL for production use",
            ])
            result["recommendations"].extend([
                "Use Cloud SQL PostgreSQL or MySQL for data persistence",
                "Consider Cloud Firestore for document-based data",
            ])
        elif db_mode == "file-based":
            result["warnings"].extend([
                "H2 file-based database requires persistent storage",
                "Cloud Run does not support persistent disk storage",
                "Migration to Cloud SQL is strongly recommended",
            ])
            result["recommendations"].extend([
                "Migrate to Cloud SQL for persistent storage",
                "Use Cloud Storage for file-based data if needed",
            ])

        result["recommendations"].append(
            "H2 is suitable only for development and testing, not production deployments"
        )
        return result

    async def _migrate_to_cloud_sql(self, db_info: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate to Cloud SQL using Dedalus tools."""
        gcp_config = self.config.get("gcp", {})
        project_id = gcp_config.get("project_id")
        region = gcp_config.get("region", "us-central1")
        cloud_sql_config = gcp_config.get("database", {}).get("cloud_sql", {})

        instance_name = cloud_sql_config.get("instance_name", "app-database")
        database_name = cloud_sql_config.get("database_name", "appdb")
        tier = cloud_sql_config.get("tier", "db-f1-micro")
        db_version = cloud_sql_config.get("database_version", "POSTGRES_15")

        self.logger.info(f"Creating Cloud SQL instance: {instance_name}")

        # Use Dedalus tool to create Cloud SQL
        raw = await create_cloud_sql_instance(
            project_id, region, instance_name, database_name, tier, db_version,
        )
        data = json.loads(raw)

        if not data.get("success"):
            return {
                "action_taken": "migrated_to_cloud_sql",
                "success": False,
                "errors": [data.get("error", "Unknown error")],
            }

        return {
            "action_taken": "migrated_to_cloud_sql",
            "success": True,
            "cloud_sql_config": data,
            "recommendations": [
                "Update Spring Boot application.properties with Cloud SQL configuration",
                "Configure Cloud SQL Proxy for local development",
                "Set up automated backups for Cloud SQL",
            ],
            "warnings": [
                "Database credentials need to be configured as environment variables in Cloud Run"
            ],
        }

    async def _get_ai_recommendations(self, db_info: Dict[str, Any], strategy: str) -> list[str]:
        """Get AI-powered database recommendations using Dedalus multi-model handoffs.

        Hands off between REASONING model (for analysis) and PLANNING model
        (for migration strategy), with Brave Search MCP for best practices.
        """
        try:
            prompt = f"""Given this database configuration and migration strategy, provide 2-3 specific recommendations:

Database Type: {db_info.get('type', 'unknown')}
Database Mode: {db_info.get('mode', 'unknown')}
Migration Strategy: {strategy}

Provide practical recommendations for data persistence, connection pooling, and security.
Format your response as a JSON array of strings."""

            response = await self.run_with_dedalus(
                prompt=prompt,
                # Multi-model: reasoning for analysis, planning for recommendations
                model=[ModelRole.REASONING.value, ModelRole.PLANNING.value],
                tools=DATABASE_TOOLS,
                mcp_servers=["windsor/brave-search-mcp"],
                instructions="You are a database migration expert specializing in cloud databases.",
                max_steps=5,
            )

            try:
                recommendations = json.loads(response)
                if isinstance(recommendations, list):
                    return recommendations
            except json.JSONDecodeError:
                lines = response.strip().split("\n")
                return [
                    line.strip() for line in lines
                    if line.strip() and not line.startswith("[") and not line.startswith("]")
                ][:3]

        except Exception as e:
            self.logger.warning(f"Could not get AI recommendations: {str(e)}")

        return []
