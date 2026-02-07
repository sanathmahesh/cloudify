"""Infrastructure Provisioning Agent — sets up GCP resources for the migration.

Responsibilities:
- Enable required GCP APIs
- Create Artifact Registry repository
- Configure Docker authentication
- Set up Firebase project for hosting
- Manage IAM permissions
"""

from __future__ import annotations

from typing import Any, Dict, List

from agents.base import BaseAgent
from utils.gcp import GCPClient
from utils.logger import get_logger

log = get_logger(__name__)

REQUIRED_SERVICES = [
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "sqladmin.googleapis.com",
    "firebase.googleapis.com",
    "firebasehosting.googleapis.com",
]


class InfraProvisionerAgent(BaseAgent):
    name = "infra_provisioner"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.gcp = GCPClient(self.config.gcp, dry_run=self.dry_run)
        self._provisioned: List[str] = []

    # -- Tools ----------------------------------------------------------------

    def _enable_gcp_services(self, services: list[str]) -> str:
        """Enable a list of GCP API services for the project.

        Args:
            services: List of GCP API service names to enable.

        Returns:
            Status message.
        """
        result = self.gcp.enable_services(services)
        if result.success:
            return f"Enabled services: {', '.join(services)}"
        return f"Failed to enable services: {result.stderr}"

    def _create_artifact_registry(self, repo_name: str) -> str:
        """Create a Docker repository in Artifact Registry.

        Args:
            repo_name: Name for the Artifact Registry repository.

        Returns:
            Status message.
        """
        result = self.gcp.create_artifact_repo(repo_name)
        if result.success or "already exists" in result.stderr:
            self._provisioned.append(f"artifact-registry:{repo_name}")
            return f"Artifact Registry repo '{repo_name}' is ready"
        return f"Failed to create repo: {result.stderr}"

    def _configure_docker_auth(self) -> str:
        """Configure Docker to authenticate with Artifact Registry.

        Returns:
            Status message.
        """
        result = self.gcp.docker_auth()
        return "Docker auth configured" if result.success else f"Failed: {result.stderr}"

    def _set_gcp_project(self) -> str:
        """Set the active GCP project.

        Returns:
            Status message.
        """
        result = self.gcp.set_project()
        return "Project set" if result.success else f"Failed: {result.stderr}"

    # -- Agent interface -------------------------------------------------------

    def get_tools(self) -> list:
        return [
            self._enable_gcp_services,
            self._create_artifact_registry,
            self._configure_docker_auth,
            self._set_gcp_project,
        ]

    def get_prompt(self) -> str:
        return (
            "You are an infrastructure provisioning agent for GCP. "
            "Set up all required cloud resources for deploying a Spring Boot "
            "backend to Cloud Run and a React frontend to Firebase Hosting. "
            "Steps: 1) Set the GCP project, 2) Enable required APIs, "
            "3) Create Artifact Registry repo, 4) Configure Docker auth."
        )

    async def execute(self) -> Dict[str, Any]:
        """Provision GCP infrastructure."""
        project = self.config.gcp.project_id
        region = self.config.gcp.region
        repo_name = "cloud-run-images"

        self.log.info(f"Provisioning GCP infrastructure for project: {project}")

        # Step 1: Set project
        self.gcp.set_project()

        # Step 2: Enable APIs
        self.log.info("Enabling required GCP services...")
        svc_result = self.gcp.enable_services(REQUIRED_SERVICES)
        if not svc_result.success and not self.dry_run:
            raise RuntimeError(f"Failed to enable services: {svc_result.stderr}")
        self._provisioned.append("services")

        # Step 3: Create Artifact Registry
        self.log.info("Creating Artifact Registry repository...")
        ar_result = self.gcp.create_artifact_repo(repo_name)
        if not ar_result.success and "already exists" not in ar_result.stderr and not self.dry_run:
            raise RuntimeError(f"Failed to create Artifact Registry: {ar_result.stderr}")
        self._provisioned.append(f"artifact-registry:{repo_name}")

        # Step 4: Docker auth
        self.log.info("Configuring Docker authentication...")
        auth_result = self.gcp.docker_auth()
        if not auth_result.success and not self.dry_run:
            raise RuntimeError(f"Failed to configure Docker auth: {auth_result.stderr}")

        image_base = f"{region}-docker.pkg.dev/{project}/{repo_name}"

        output = {
            "project_id": project,
            "region": region,
            "artifact_registry_repo": repo_name,
            "image_base_url": image_base,
            "services_enabled": REQUIRED_SERVICES,
        }

        self.state.set_artifact("infra", output)
        if self.dry_run:
            self.state.dry_run_scripts.extend(self.gcp.scripts)

        self.log.info(f"Infrastructure ready. Image base: {image_base}")
        return output

    async def rollback(self) -> None:
        """Remove provisioned resources."""
        self.log.info("Rolling back infrastructure provisioning...")
        for resource in reversed(self._provisioned):
            if resource.startswith("artifact-registry:"):
                repo_name = resource.split(":")[1]
                self.log.info(f"Deleting Artifact Registry repo: {repo_name}")
                from utils.shell import run_command
                run_command(
                    f"gcloud artifacts repositories delete {repo_name} "
                    f"--location={self.config.gcp.region} "
                    f"--project={self.config.gcp.project_id} --quiet"
                )
        self.agent_state.mark_rolled_back()
