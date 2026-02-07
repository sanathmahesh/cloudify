"""
GCP helper utilities for common operations.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional


class GCPHelper:
    """Helper class for GCP operations."""

    def __init__(self, project_id: str, region: str = "us-central1"):
        """
        Initialize GCP helper.

        Args:
            project_id: GCP project ID
            region: GCP region
        """
        self.project_id = project_id
        self.region = region
        self.logger = logging.getLogger(self.__class__.__name__)

    async def run_gcloud_command(
        self, command: str, capture_output: bool = True
    ) -> Dict[str, Any]:
        """
        Run a gcloud command.

        Args:
            command: Command to run (without 'gcloud' prefix)
            capture_output: Whether to capture output

        Returns:
            Dictionary with returncode, stdout, stderr
        """
        full_command = f"gcloud {command}"

        try:
            if capture_output:
                process = await asyncio.create_subprocess_shell(
                    full_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await process.communicate()

                return {
                    "success": process.returncode == 0,
                    "returncode": process.returncode,
                    "stdout": stdout.decode() if stdout else "",
                    "stderr": stderr.decode() if stderr else "",
                }
            else:
                process = await asyncio.create_subprocess_shell(full_command)
                await process.wait()

                return {
                    "success": process.returncode == 0,
                    "returncode": process.returncode,
                    "stdout": "",
                    "stderr": "",
                }

        except Exception as e:
            self.logger.error(f"Error running gcloud command: {str(e)}")
            return {
                "success": False,
                "returncode": 1,
                "stdout": "",
                "stderr": str(e),
            }

    async def check_project_exists(self) -> bool:
        """Check if GCP project exists."""
        result = await self.run_gcloud_command(
            f"projects describe {self.project_id}"
        )
        return result["success"]

    async def enable_api(self, api: str) -> bool:
        """
        Enable a GCP API.

        Args:
            api: API name (e.g., 'run.googleapis.com')

        Returns:
            True if successful
        """
        result = await self.run_gcloud_command(
            f"services enable {api} --project={self.project_id}"
        )
        return result["success"]

    async def list_cloud_run_services(self) -> List[Dict[str, Any]]:
        """
        List Cloud Run services in the project.

        Returns:
            List of service information dictionaries
        """
        result = await self.run_gcloud_command(
            f"run services list --region={self.region} "
            f"--project={self.project_id} --format=json"
        )

        if result["success"] and result["stdout"]:
            try:
                return json.loads(result["stdout"])
            except json.JSONDecodeError:
                return []

        return []

    async def get_service_url(self, service_name: str) -> Optional[str]:
        """
        Get Cloud Run service URL.

        Args:
            service_name: Name of the Cloud Run service

        Returns:
            Service URL or None
        """
        result = await self.run_gcloud_command(
            f"run services describe {service_name} "
            f"--region={self.region} "
            f"--project={self.project_id} "
            f"--format='value(status.url)'"
        )

        if result["success"]:
            return result["stdout"].strip()

        return None

    async def create_secret(
        self, secret_name: str, secret_value: str
    ) -> bool:
        """
        Create a secret in Secret Manager.

        Args:
            secret_name: Secret name
            secret_value: Secret value

        Returns:
            True if successful
        """
        # Create secret
        create_result = await self.run_gcloud_command(
            f"secrets create {secret_name} "
            f"--replication-policy=automatic "
            f"--project={self.project_id}"
        )

        if not create_result["success"]:
            # Secret might already exist
            if "already exists" not in create_result["stderr"]:
                return False

        # Add secret version
        process = await asyncio.create_subprocess_shell(
            f"echo -n '{secret_value}' | gcloud secrets versions add {secret_name} "
            f"--data-file=- --project={self.project_id}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        await process.communicate()
        return process.returncode == 0

    async def get_project_number(self) -> Optional[str]:
        """
        Get GCP project number.

        Returns:
            Project number or None
        """
        result = await self.run_gcloud_command(
            f"projects describe {self.project_id} "
            f"--format='value(projectNumber)'"
        )

        if result["success"]:
            return result["stdout"].strip()

        return None

    async def grant_iam_role(
        self, member: str, role: str
    ) -> bool:
        """
        Grant IAM role to a member.

        Args:
            member: Member identifier (e.g., 'serviceAccount:...')
            role: Role to grant (e.g., 'roles/run.admin')

        Returns:
            True if successful
        """
        result = await self.run_gcloud_command(
            f"projects add-iam-policy-binding {self.project_id} "
            f"--member={member} --role={role}"
        )

        return result["success"]
