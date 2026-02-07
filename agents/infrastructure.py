"""
Infrastructure Provisioning Agent — Powered by Dedalus SDK

Creates and configures GCP resources using:
- PLANNING model (Claude Sonnet) for intelligent infrastructure decisions
- Local tools for GCP CLI operations
- Dedalus tool calling for all provisioning steps
"""

import json
from typing import Any, Dict

from .base_agent import AgentResult, AgentStatus, BaseAgent, Event, EventType, ModelRole
from .dedalus_tools import (
    INFRASTRUCTURE_TOOLS,
    check_gcloud_auth,
    configure_iam_permissions,
    create_artifact_registry,
    enable_gcp_apis,
    setup_firebase_project,
)


class InfrastructureAgent(BaseAgent):
    """
    Infrastructure agent powered by Dedalus SDK.

    Uses the PLANNING model for infrastructure decisions and local tools
    for all GCP provisioning operations.
    """

    def __init__(self, event_bus, config: Dict[str, Any], dedalus_api_key: str):
        super().__init__(
            name="Infrastructure",
            event_bus=event_bus,
            config=config,
            dedalus_api_key=dedalus_api_key,
        )

    async def _execute_impl(self) -> AgentResult:
        """Execute infrastructure provisioning via Dedalus tools."""
        self.logger.info("Starting infrastructure provisioning with Dedalus PLANNING model")

        gcp_config = self.config.get("gcp", {})
        project_id = gcp_config.get("project_id")
        region = gcp_config.get("region", "us-central1")

        if not project_id:
            return AgentResult(
                status=AgentStatus.FAILED,
                data={},
                errors=["GCP project_id not specified in configuration"],
            )

        warnings: list[str] = []
        errors: list[str] = []
        provisioned: Dict[str, Any] = {
            "project": {},
            "artifact_registry": {},
            "firebase": {},
            "iam": {},
        }

        try:
            # Step 1: Check gcloud auth (tool call)
            auth_raw = await check_gcloud_auth()
            auth_data = json.loads(auth_raw)

            if not auth_data.get("installed"):
                return AgentResult(
                    status=AgentStatus.FAILED,
                    data={},
                    errors=["gcloud CLI not installed. Please install Google Cloud SDK."],
                )

            if not auth_data.get("authenticated"):
                return AgentResult(
                    status=AgentStatus.FAILED,
                    data={},
                    errors=["Not authenticated with gcloud. Run 'gcloud auth login' first."],
                )

            provisioned["project"] = {"project_id": project_id, "region": region}

            # Step 2: Enable APIs (tool call)
            self.logger.info("Enabling required GCP APIs")
            apis_raw = await enable_gcp_apis(
                project_id,
                ["run.googleapis.com", "artifactregistry.googleapis.com",
                 "cloudbuild.googleapis.com", "firebase.googleapis.com"],
            )
            apis_data = json.loads(apis_raw)
            failed_apis = [k for k, v in apis_data.items() if "failed" in v]
            if failed_apis:
                warnings.append(f"Some APIs failed to enable: {failed_apis}")

            # Step 3: Create Artifact Registry (tool call)
            self.logger.info("Creating Artifact Registry repository")
            repo_name = gcp_config.get("artifact_registry", {}).get("repository_name", "cloudify-apps")
            registry_raw = await create_artifact_registry(project_id, region, repo_name)
            registry_data = json.loads(registry_raw)
            if registry_data.get("success"):
                provisioned["artifact_registry"] = {
                    "repository_name": repo_name,
                    "repository_url": registry_data["repository_url"],
                    "location": region,
                    "format": "docker",
                }
            else:
                warnings.append(f"Artifact Registry: {registry_data.get('error')}")

            # Step 4: Set up Firebase (tool call)
            self.logger.info("Setting up Firebase project")
            firebase_raw = await setup_firebase_project(project_id)
            firebase_data = json.loads(firebase_raw)
            if firebase_data.get("success"):
                provisioned["firebase"] = {
                    "project_id": project_id,
                    "hosting_site": firebase_data["hosting_site"],
                }
            else:
                warnings.append(f"Firebase setup: {firebase_data.get('error')}")

            # Step 5: Configure IAM (tool call)
            self.logger.info("Configuring IAM permissions")
            iam_raw = await configure_iam_permissions(project_id)
            iam_data = json.loads(iam_raw)
            if iam_data.get("success"):
                provisioned["iam"] = iam_data
            else:
                warnings.append(f"IAM configuration: {iam_data.get('error')}")

            # Step 6: Use Dedalus PLANNING model for infrastructure review
            try:
                review = await self.run_with_dedalus(
                    prompt=(
                        f"Review this GCP infrastructure setup and suggest any improvements:\n"
                        f"{json.dumps(provisioned, indent=2)}\n\n"
                        f"Provide 1-2 brief recommendations."
                    ),
                    model=ModelRole.PLANNING.value,
                    tools=INFRASTRUCTURE_TOOLS,
                    instructions="You are a GCP infrastructure expert. Be concise.",
                    max_steps=3,
                )
                if review:
                    provisioned["ai_review"] = review
            except Exception as e:
                self.logger.warning(f"AI review skipped: {e}")

            # Publish infrastructure ready event
            await self.event_bus.publish(Event(
                event_type=EventType.INFRASTRUCTURE_READY,
                source_agent=self.name,
                data=provisioned,
            ))

            return AgentResult(
                status=AgentStatus.SUCCESS if not errors else AgentStatus.FAILED,
                data={
                    "summary": provisioned,
                    "project_id": project_id,
                    "region": region,
                    "artifact_registry_repo": provisioned["artifact_registry"].get("repository_url"),
                },
                errors=errors,
                warnings=warnings,
            )

        except Exception as e:
            self.logger.error(f"Infrastructure provisioning error: {str(e)}", exc_info=True)
            return AgentResult(
                status=AgentStatus.FAILED,
                data=provisioned,
                errors=[str(e)],
                warnings=warnings,
            )
