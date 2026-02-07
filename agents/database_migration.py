"""
Database Migration Agent

Handles database migration from H2 to Cloud SQL or provides warnings.
"""

import asyncio
from typing import Any, Dict

from .base_agent import AgentResult, AgentStatus, BaseAgent, Event, EventType


class DatabaseMigrationAgent(BaseAgent):
    """
    Database Migration agent that handles database setup.

    Responsibilities:
    - Analyze H2 database mode (in-memory vs file-based)
    - Recommend Cloud SQL setup OR keep H2 with warnings
    - Optionally migrate data to Cloud SQL
    - Update Spring Boot datasource configuration
    """

    def __init__(self, event_bus, config: Dict[str, Any], claude_api_key: str):
        super().__init__(
            name="DatabaseMigration",
            event_bus=event_bus,
            config=config,
            claude_api_key=claude_api_key,
        )

    async def _execute_impl(self) -> AgentResult:
        """Execute database migration analysis and recommendations."""
        self.logger.info("Starting database migration analysis")

        # Get analysis results from code analyzer
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

        warnings = []
        migration_result = {
            "strategy": db_strategy,
            "database_type": db_info.get("type", "unknown"),
            "database_mode": db_info.get("mode", "unknown"),
            "action_taken": None,
            "recommendations": [],
        }

        try:
            if db_strategy == "keep-h2":
                self.logger.info("Keeping H2 database configuration")
                result = await self._keep_h2_strategy(db_info)
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

            # Use Claude to generate additional recommendations
            ai_recommendations = await self._get_ai_recommendations(db_info, db_strategy)
            migration_result["recommendations"].extend(ai_recommendations)

            # Publish database migrated event
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

    async def _keep_h2_strategy(self, db_info: Dict[str, Any]) -> Dict[str, Any]:
        """Keep H2 database with appropriate warnings."""
        result = {
            "action_taken": "kept_h2",
            "warnings": [],
            "recommendations": [],
        }

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
                "Implement data export/import scripts for development",
            ])

        elif db_mode == "file-based":
            result["warnings"].extend([
                "H2 file-based database requires persistent storage",
                "Cloud Run does not support persistent disk storage",
                "Files will be lost when container restarts",
                "Migration to Cloud SQL is strongly recommended",
            ])
            result["recommendations"].extend([
                "Migrate to Cloud SQL for persistent storage",
                "Use Cloud Storage for file-based data if needed",
                "Consider containerizing with volume mounts for development only",
            ])

        else:
            result["warnings"].append("Unknown H2 database mode detected")

        result["recommendations"].append(
            "H2 is suitable only for development and testing, not production deployments"
        )

        return result

    async def _migrate_to_cloud_sql(self, db_info: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate to Cloud SQL."""
        result = {
            "action_taken": "migrated_to_cloud_sql",
            "success": False,
            "errors": [],
            "warnings": [],
            "recommendations": [],
            "cloud_sql_config": {},
        }

        try:
            gcp_config = self.config.get("gcp", {})
            project_id = gcp_config.get("project_id")
            region = gcp_config.get("region", "us-central1")

            cloud_sql_config = gcp_config.get("database", {}).get("cloud_sql", {})
            instance_name = cloud_sql_config.get("instance_name", "app-database")
            database_name = cloud_sql_config.get("database_name", "appdb")
            tier = cloud_sql_config.get("tier", "db-f1-micro")
            db_version = cloud_sql_config.get("database_version", "POSTGRES_15")

            # Create Cloud SQL instance
            self.logger.info(f"Creating Cloud SQL instance: {instance_name}")

            create_cmd = (
                f"gcloud sql instances create {instance_name} "
                f"--database-version={db_version} "
                f"--tier={tier} "
                f"--region={region} "
                f"--project={project_id}"
            )

            create_result = await self._run_command(create_cmd)

            if create_result["returncode"] != 0:
                # Check if instance already exists
                if "already exists" in create_result["stderr"]:
                    self.logger.info(f"Cloud SQL instance '{instance_name}' already exists")
                else:
                    result["errors"].append(f"Failed to create Cloud SQL instance: {create_result['stderr']}")
                    return result

            # Create database
            self.logger.info(f"Creating database: {database_name}")
            db_cmd = (
                f"gcloud sql databases create {database_name} "
                f"--instance={instance_name} "
                f"--project={project_id}"
            )
            await self._run_command(db_cmd)

            # Get connection name
            conn_cmd = (
                f"gcloud sql instances describe {instance_name} "
                f"--project={project_id} "
                f"--format='value(connectionName)'"
            )
            conn_result = await self._run_command(conn_cmd)
            connection_name = conn_result["stdout"].strip() if conn_result["returncode"] == 0 else ""

            result["cloud_sql_config"] = {
                "instance_name": instance_name,
                "database_name": database_name,
                "connection_name": connection_name,
                "tier": tier,
                "database_version": db_version,
            }

            result["success"] = True
            result["recommendations"].extend([
                "Update Spring Boot application.properties with Cloud SQL configuration",
                "Configure Cloud SQL Proxy for local development",
                "Set up automated backups for Cloud SQL",
                "Consider read replicas for high availability",
            ])

            result["warnings"].append(
                "Database credentials need to be configured as environment variables in Cloud Run"
            )

        except Exception as e:
            result["errors"].append(str(e))
            return result

        return result

    async def _get_ai_recommendations(
        self, db_info: Dict[str, Any], strategy: str
    ) -> list:
        """Get AI-powered recommendations for database migration."""
        try:
            prompt = f"""
Given the following database configuration and migration strategy, provide 2-3 specific recommendations:

Database Type: {db_info.get('type', 'unknown')}
Database Mode: {db_info.get('mode', 'unknown')}
Migration Strategy: {strategy}

Provide practical recommendations for:
1. Data persistence and reliability
2. Connection pooling and performance
3. Security best practices

Format your response as a JSON array of strings.
"""

            response = await self.ask_claude(
                prompt=prompt,
                system_prompt="You are a database migration expert specializing in cloud databases.",
                max_tokens=1000,
            )

            # Parse response
            import json
            try:
                recommendations = json.loads(response)
                if isinstance(recommendations, list):
                    return recommendations
            except json.JSONDecodeError:
                lines = response.strip().split("\n")
                return [line.strip() for line in lines if line.strip() and not line.startswith("[") and not line.startswith("]")][:3]

        except Exception as e:
            self.logger.warning(f"Could not get AI recommendations: {str(e)}")

        return []

    async def _run_command(self, command: str) -> Dict[str, Any]:
        """Run shell command asynchronously."""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            return {
                "returncode": process.returncode,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
            }

        except Exception as e:
            return {
                "returncode": 1,
                "stdout": "",
                "stderr": str(e),
            }
