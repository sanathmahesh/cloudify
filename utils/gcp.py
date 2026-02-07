"""Wrapper around gcloud / firebase CLI commands for GCP resource management."""

from __future__ import annotations

from typing import Dict, List, Optional

from utils.config import GCPConfig
from utils.logger import get_logger
from utils.shell import CommandResult, run_command

log = get_logger(__name__)


class GCPClient:
    """Thin wrapper that builds and executes gcloud CLI commands."""

    def __init__(self, config: GCPConfig, dry_run: bool = False) -> None:
        self.config = config
        self.dry_run = dry_run
        self._scripts: List[str] = []

    @property
    def scripts(self) -> List[str]:
        return list(self._scripts)

    def _run(self, cmd: str, **kwargs) -> CommandResult:
        self._scripts.append(cmd)
        if self.dry_run:
            log.info(f"[DRY RUN] {cmd}")
            return CommandResult(returncode=0, stdout="dry-run", stderr="", command=cmd)
        return run_command(cmd, **kwargs)

    # -- Project ---------------------------------------------------------------

    def set_project(self) -> CommandResult:
        return self._run(f"gcloud config set project {self.config.project_id}")

    def enable_services(self, services: List[str]) -> CommandResult:
        svc = " ".join(services)
        return self._run(f"gcloud services enable {svc} --project={self.config.project_id}")

    # -- Artifact Registry -----------------------------------------------------

    def create_artifact_repo(self, repo_name: str = "cloud-run-images") -> CommandResult:
        return self._run(
            f"gcloud artifacts repositories create {repo_name} "
            f"--repository-format=docker "
            f"--location={self.config.region} "
            f"--project={self.config.project_id} "
            f"--quiet"
        )

    def docker_auth(self) -> CommandResult:
        return self._run(
            f"gcloud auth configure-docker {self.config.region}-docker.pkg.dev --quiet"
        )

    # -- Cloud Run -------------------------------------------------------------

    def deploy_cloud_run(
        self,
        service_name: str,
        image: str,
        port: int = 8080,
        memory: str = "512Mi",
        cpu: str = "1",
        min_instances: int = 0,
        max_instances: int = 3,
        env_vars: Optional[Dict[str, str]] = None,
        allow_unauthenticated: bool = True,
    ) -> CommandResult:
        cmd = (
            f"gcloud run deploy {service_name} "
            f"--image={image} "
            f"--port={port} "
            f"--memory={memory} "
            f"--cpu={cpu} "
            f"--min-instances={min_instances} "
            f"--max-instances={max_instances} "
            f"--region={self.config.region} "
            f"--project={self.config.project_id} "
            f"--quiet"
        )
        if allow_unauthenticated:
            cmd += " --allow-unauthenticated"
        if env_vars:
            pairs = ",".join(f"{k}={v}" for k, v in env_vars.items())
            cmd += f" --set-env-vars={pairs}"
        return self._run(cmd)

    def get_cloud_run_url(self, service_name: str) -> Optional[str]:
        result = self._run(
            f"gcloud run services describe {service_name} "
            f"--region={self.config.region} "
            f"--project={self.config.project_id} "
            f"--format='value(status.url)'"
        )
        if result.success and result.stdout:
            return result.stdout.strip().strip("'")
        return None

    def delete_cloud_run(self, service_name: str) -> CommandResult:
        return self._run(
            f"gcloud run services delete {service_name} "
            f"--region={self.config.region} "
            f"--project={self.config.project_id} "
            f"--quiet"
        )

    # -- Cloud SQL -------------------------------------------------------------

    def create_cloudsql_instance(
        self,
        instance_name: str,
        tier: str = "db-f1-micro",
        database_version: str = "POSTGRES_15",
    ) -> CommandResult:
        return self._run(
            f"gcloud sql instances create {instance_name} "
            f"--database-version={database_version} "
            f"--tier={tier} "
            f"--region={self.config.region} "
            f"--project={self.config.project_id} "
            f"--quiet"
        )

    def create_cloudsql_database(
        self, instance_name: str, database_name: str
    ) -> CommandResult:
        return self._run(
            f"gcloud sql databases create {database_name} "
            f"--instance={instance_name} "
            f"--project={self.config.project_id} "
            f"--quiet"
        )

    def delete_cloudsql_instance(self, instance_name: str) -> CommandResult:
        return self._run(
            f"gcloud sql instances delete {instance_name} "
            f"--project={self.config.project_id} "
            f"--quiet"
        )

    # -- Firebase --------------------------------------------------------------

    def firebase_init_hosting(self, project_dir: str) -> CommandResult:
        return self._run(
            f"firebase init hosting --project={self.config.project_id}",
            cwd=project_dir,
        )

    def firebase_deploy_hosting(self, project_dir: str) -> CommandResult:
        return self._run(
            f"firebase deploy --only hosting --project={self.config.project_id}",
            cwd=project_dir,
        )

    # -- Docker ----------------------------------------------------------------

    def docker_build(self, tag: str, context_dir: str) -> CommandResult:
        return self._run(f"docker build -t {tag} .", cwd=context_dir, timeout=600)

    def docker_push(self, tag: str) -> CommandResult:
        return self._run(f"docker push {tag}", timeout=600)
