"""
Infrastructure Provisioning Agent

Creates and configures GCP resources for the migrated application.
"""

import asyncio
import json
import subprocess
from typing import Any, Dict, List

from .base_agent import AgentResult, AgentStatus, BaseAgent, Event, EventType


class InfrastructureAgent(BaseAgent):
    """
    Infrastructure agent that provisions GCP resources.

    Responsibilities:
    - Create GCP project resources using gcloud CLI
    - Set up Cloud Run service
    - Configure Artifact Registry
    - Set up Firebase project for hosting
    - Manage IAM permissions
    """

    def __init__(self, event_bus, config: Dict[str, Any], claude_api_key: str):
        super().__init__(
            name="Infrastructure",
            event_bus=event_bus,
            config=config,
            claude_api_key=claude_api_key,
        )

    async def _execute_impl(self) -> AgentResult:
        """Execute infrastructure provisioning."""
        self.logger.info("Starting infrastructure provisioning")

        gcp_config = self.config.get("gcp", {})
        project_id = gcp_config.get("project_id")
        region = gcp_config.get("region", "us-central1")

        if not project_id:
            return AgentResult(
                status=AgentStatus.FAILED,
                data={},
                errors=["GCP project_id not specified in configuration"],
            )

        warnings = []
        errors = []
        provisioned = {
            "project": {},
            "artifact_registry": {},
            "cloud_run": {},
            "firebase": {},
            "iam": {},
        }

        try:
            # Check gcloud CLI installation
            if not await self._check_gcloud_installed():
                return AgentResult(
                    status=AgentStatus.FAILED,
                    data={},
                    errors=["gcloud CLI not installed. Please install Google Cloud SDK."],
                )

            # Authenticate with GCP
            auth_result = await self._authenticate_gcp()
            if not auth_result["success"]:
                return AgentResult(
                    status=AgentStatus.FAILED,
                    data={},
                    errors=[f"GCP authentication failed: {auth_result.get('error')}"],
                )

            # Set project
            await self._run_gcloud(f"config set project {project_id}")
            provisioned["project"] = {"project_id": project_id, "region": region}

            # Enable required APIs
            self.logger.info("Enabling required GCP APIs")
            apis_result = await self._enable_apis(project_id)
            if not apis_result["success"]:
                warnings.append(f"Some APIs failed to enable: {apis_result.get('error')}")

            # Create Artifact Registry repository
            self.logger.info("Creating Artifact Registry repository")
            registry_result = await self._create_artifact_registry(project_id, region)
            if registry_result["success"]:
                provisioned["artifact_registry"] = registry_result["data"]
            else:
                warnings.append(f"Artifact Registry: {registry_result.get('error')}")

            # Set up Firebase (for frontend hosting)
            self.logger.info("Setting up Firebase project")
            firebase_result = await self._setup_firebase(project_id)
            if firebase_result["success"]:
                provisioned["firebase"] = firebase_result["data"]
            else:
                warnings.append(f"Firebase setup: {firebase_result.get('error')}")

            # Configure IAM permissions
            self.logger.info("Configuring IAM permissions")
            iam_result = await self._configure_iam(project_id)
            if iam_result["success"]:
                provisioned["iam"] = iam_result["data"]
            else:
                warnings.append(f"IAM configuration: {iam_result.get('error')}")

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

    async def _check_gcloud_installed(self) -> bool:
        """Check if gcloud CLI is installed."""
        try:
            result = await self._run_command("gcloud --version")
            return result["returncode"] == 0
        except Exception:
            return False

    async def _authenticate_gcp(self) -> Dict[str, Any]:
        """Authenticate with GCP."""
        try:
            service_account_key = self.config.get("gcp", {}).get("service_account_key")

            if service_account_key:
                # Authenticate with service account
                self.logger.info("Authenticating with service account key")
                result = await self._run_gcloud(
                    f"auth activate-service-account --key-file={service_account_key}"
                )
                if result["returncode"] == 0:
                    return {"success": True}
                else:
                    return {"success": False, "error": result.get("stderr")}
            else:
                # Use Application Default Credentials
                self.logger.info("Checking for existing authentication")

                # Check if already authenticated FIRST
                check_result = await self._run_command("gcloud auth list")
                if check_result["returncode"] == 0 and check_result["stdout"]:
                    # Check for active account
                    if "*" in check_result["stdout"] or "ACTIVE" in check_result["stdout"]:
                        self.logger.info("Already authenticated with gcloud")
                        return {"success": True}

                # If not authenticated, fail with clear instructions
                return {
                    "success": False,
                    "error": "Not authenticated with gcloud. Please run 'gcloud auth login' or 'gcloud auth application-default login' before running the migration."
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _enable_apis(self, project_id: str) -> Dict[str, Any]:
        """Enable required GCP APIs."""
        required_apis = [
            "run.googleapis.com",
            "artifactregistry.googleapis.com",
            "cloudbuild.googleapis.com",
            "firebase.googleapis.com",
        ]

        try:
            for api in required_apis:
                self.logger.info(f"Enabling API: {api}")
                await self._run_gcloud(f"services enable {api} --project={project_id}")

            return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _create_artifact_registry(
        self, project_id: str, region: str
    ) -> Dict[str, Any]:
        """Create Artifact Registry repository."""
        try:
            repo_config = self.config.get("gcp", {}).get("artifact_registry", {})
            repo_name = repo_config.get("repository_name", "cloudify-apps")
            repo_format = repo_config.get("format", "docker")
            description = repo_config.get("description", "Migrated application images")

            # Check if repository already exists
            check_cmd = f"artifacts repositories describe {repo_name} --location={region}"
            check_result = await self._run_gcloud(check_cmd)

            if check_result["returncode"] == 0:
                self.logger.info(f"Artifact Registry repository '{repo_name}' already exists")
            else:
                # Create repository
                create_cmd = (
                    f"artifacts repositories create {repo_name} "
                    f"--repository-format={repo_format} "
                    f"--location={region} "
                    f"--description='{description}'"
                )
                result = await self._run_gcloud(create_cmd)

                if result["returncode"] != 0:
                    return {"success": False, "error": result.get("stderr")}

            repository_url = f"{region}-docker.pkg.dev/{project_id}/{repo_name}"

            return {
                "success": True,
                "data": {
                    "repository_name": repo_name,
                    "repository_url": repository_url,
                    "location": region,
                    "format": repo_format,
                }
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _setup_firebase(self, project_id: str) -> Dict[str, Any]:
        """Set up Firebase project for hosting."""
        try:
            # Check if firebase CLI is installed
            firebase_check = await self._run_command("firebase --version")
            if firebase_check["returncode"] != 0:
                self.logger.warning("Firebase CLI not installed")
                return {
                    "success": False,
                    "error": "Firebase CLI not installed. Run: npm install -g firebase-tools"
                }

            # Firebase project is typically the same as GCP project
            return {
                "success": True,
                "data": {
                    "project_id": project_id,
                    "hosting_site": f"{project_id}.web.app",
                    "note": "Firebase hosting will be configured during frontend deployment"
                }
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _configure_iam(self, project_id: str) -> Dict[str, Any]:
        """Configure IAM permissions."""
        try:
            # Get current project number
            result = await self._run_gcloud(
                f"projects describe {project_id} --format='value(projectNumber)'"
            )

            if result["returncode"] == 0:
                project_number = result["stdout"].strip()

                # Grant Cloud Run permissions to the Cloud Build service account
                service_account = f"{project_number}@cloudbuild.gserviceaccount.com"
                roles = [
                    "roles/run.admin",
                    "roles/iam.serviceAccountUser",
                ]

                for role in roles:
                    await self._run_gcloud(
                        f"projects add-iam-policy-binding {project_id} "
                        f"--member=serviceAccount:{service_account} "
                        f"--role={role}"
                    )

                return {
                    "success": True,
                    "data": {
                        "project_number": project_number,
                        "service_account": service_account,
                        "roles_granted": roles,
                    }
                }
            else:
                return {"success": False, "error": "Could not get project number"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _run_gcloud(self, command: str) -> Dict[str, Any]:
        """Run gcloud command."""
        full_command = f"gcloud {command}"
        return await self._run_command(full_command)

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
