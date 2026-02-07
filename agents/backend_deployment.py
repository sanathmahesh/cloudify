"""
Backend Deployment Agent

Deploys Spring Boot application to Google Cloud Run.
"""

import asyncio
import os
import re
from pathlib import Path
from typing import Any, Dict

from .base_agent import AgentResult, AgentStatus, BaseAgent, Event, EventType


class BackendDeploymentAgent(BaseAgent):
    """
    Backend Deployment agent that deploys Spring Boot to Cloud Run.

    Responsibilities:
    - Generate optimized Dockerfile for Spring Boot
    - Update application.properties with GCP configurations
    - Build Docker image
    - Push to Artifact Registry
    - Deploy to Cloud Run
    - Configure environment variables and secrets
    """

    def __init__(self, event_bus, config: Dict[str, Any], claude_api_key: str):
        super().__init__(
            name="BackendDeployment",
            event_bus=event_bus,
            config=config,
            claude_api_key=claude_api_key,
        )

    async def _execute_impl(self) -> AgentResult:
        """Execute backend deployment."""
        self.logger.info("Starting backend deployment")

        # Get infrastructure information
        infra_events = self.event_bus.get_history(EventType.INFRASTRUCTURE_READY)
        if not infra_events:
            return AgentResult(
                status=AgentStatus.FAILED,
                data={},
                errors=["Infrastructure not provisioned. Run infrastructure agent first."],
            )

        infra_data = infra_events[-1].data
        artifact_registry = infra_data.get("artifact_registry", {})
        registry_url = artifact_registry.get("repository_url")

        if not registry_url:
            return AgentResult(
                status=AgentStatus.FAILED,
                data={},
                errors=["Artifact Registry repository URL not found"],
            )

        # Get analysis data
        analysis_events = self.event_bus.get_history(EventType.ANALYSIS_COMPLETE)
        analysis_data = analysis_events[-1].data if analysis_events else {}

        warnings = []
        errors = []
        deployment_result = {
            "dockerfile_created": False,
            "image_built": False,
            "image_pushed": False,
            "service_deployed": False,
            "service_url": None,
        }

        try:
            source_path = Path(self.config["source"]["path"])
            backend_path = source_path / self.config["source"]["backend"]["path"]

            if not backend_path.exists():
                return AgentResult(
                    status=AgentStatus.FAILED,
                    data={},
                    errors=[f"Backend path not found: {backend_path}"],
                )

            # Generate Dockerfile
            self.logger.info("Generating Dockerfile")
            dockerfile_result = await self._generate_dockerfile(backend_path, analysis_data)
            if dockerfile_result["success"]:
                deployment_result["dockerfile_created"] = True
            else:
                errors.append(f"Dockerfile generation failed: {dockerfile_result.get('error')}")
                return AgentResult(
                    status=AgentStatus.FAILED,
                    data=deployment_result,
                    errors=errors,
                )

            # Update CORS configuration with frontend URL
            site_name = self.config.get("gcp", {}).get("frontend", {}).get("site_name")
            if site_name:
                frontend_url = f"https://{site_name}.web.app"
                self.logger.info(f"Updating CORS configuration for frontend: {frontend_url}")
                cors_result = await self._update_cors_configuration(backend_path, frontend_url)
                if cors_result["success"]:
                    self.logger.info(f"CORS configuration updated: {cors_result.get('files_updated', 0)} file(s)")
                else:
                    warnings.append(f"CORS update: {cors_result.get('error')}")

            # Build Docker image
            gcp_config = self.config.get("gcp", {})
            project_id = gcp_config.get("project_id")
            service_name = gcp_config.get("backend", {}).get("service_name", "app-backend")
            image_tag = f"{registry_url}/{service_name}:latest"

            self.logger.info(f"Building Docker image: {image_tag}")
            build_result = await self._build_docker_image(backend_path, image_tag)
            if build_result["success"]:
                deployment_result["image_built"] = True
            else:
                errors.append(f"Docker build failed: {build_result.get('error')}")
                return AgentResult(
                    status=AgentStatus.FAILED,
                    data=deployment_result,
                    errors=errors,
                )

            # Push image to Artifact Registry
            self.logger.info("Pushing image to Artifact Registry")
            push_result = await self._push_docker_image(image_tag)
            if push_result["success"]:
                deployment_result["image_pushed"] = True
            else:
                errors.append(f"Docker push failed: {push_result.get('error')}")
                return AgentResult(
                    status=AgentStatus.FAILED,
                    data=deployment_result,
                    errors=errors,
                )

            # Deploy to Cloud Run
            self.logger.info("Deploying to Cloud Run")
            deploy_result = await self._deploy_to_cloud_run(
                project_id,
                service_name,
                image_tag,
                gcp_config
            )
            if deploy_result["success"]:
                deployment_result["service_deployed"] = True
                deployment_result["service_url"] = deploy_result["service_url"]
            else:
                errors.append(f"Cloud Run deployment failed: {deploy_result.get('error')}")
                return AgentResult(
                    status=AgentStatus.FAILED,
                    data=deployment_result,
                    errors=errors,
                )

            # Publish backend deployed event
            await self.event_bus.publish(Event(
                event_type=EventType.BACKEND_DEPLOYED,
                source_agent=self.name,
                data={
                    "service_name": service_name,
                    "service_url": deployment_result["service_url"],
                    "image_tag": image_tag,
                },
            ))

            return AgentResult(
                status=AgentStatus.SUCCESS,
                data=deployment_result,
                warnings=warnings,
            )

        except Exception as e:
            self.logger.error(f"Backend deployment error: {str(e)}", exc_info=True)
            return AgentResult(
                status=AgentStatus.FAILED,
                data=deployment_result,
                errors=[str(e)],
            )

    async def _generate_dockerfile(
        self, backend_path: Path, analysis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate optimized Dockerfile for Spring Boot."""
        try:
            backend_analysis = analysis_data.get("backend", {})
            build_tool = backend_analysis.get("build_tool", "maven")
            java_version = backend_analysis.get("java_version", "21")

            # Use Claude to generate optimized Dockerfile
            prompt = f"""
Generate an optimized Dockerfile for a Spring Boot application with the following characteristics:
- Build tool: {build_tool}
- Java version: {java_version}
- Spring Boot version: {backend_analysis.get('spring_boot_version', '3.x')}

Requirements:
1. Multi-stage build to minimize image size
2. Use appropriate base images
3. Optimize layer caching
4. Non-root user for security
5. Health check endpoint
6. Expose port 8080

Provide ONLY the Dockerfile content, no explanations.
"""

            dockerfile_content = await self.ask_claude(
                prompt=prompt,
                system_prompt="You are a Docker expert specializing in Java applications.",
                max_tokens=1500,
            )

            # Clean up the response
            dockerfile_content = dockerfile_content.strip()
            if dockerfile_content.startswith("```dockerfile"):
                dockerfile_content = dockerfile_content.split("```dockerfile")[1]
            if dockerfile_content.startswith("```"):
                dockerfile_content = dockerfile_content.split("```")[1]
            if dockerfile_content.endswith("```"):
                dockerfile_content = dockerfile_content.rsplit("```", 1)[0]

            dockerfile_content = dockerfile_content.strip()

            # Write Dockerfile
            dockerfile_path = backend_path / "Dockerfile"
            dockerfile_path.write_text(dockerfile_content)

            self.logger.info(f"Dockerfile created at: {dockerfile_path}")

            return {"success": True, "dockerfile_path": str(dockerfile_path)}

        except Exception as e:
            self.logger.error(f"Error generating Dockerfile: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _build_docker_image(
        self, backend_path: Path, image_tag: str
    ) -> Dict[str, Any]:
        """Build Docker image."""
        try:
            # Build for linux/amd64 platform (required by Cloud Run)
            # This is especially important when building on ARM Macs (M1/M2/M3)
            build_cmd = f"docker build --platform linux/amd64 -t {image_tag} {backend_path}"

            self.logger.info(f"Building Docker image: {build_cmd}")

            result = await self._run_command(build_cmd)

            if result["returncode"] == 0:
                return {"success": True}
            else:
                return {"success": False, "error": result["stderr"]}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _push_docker_image(self, image_tag: str) -> Dict[str, Any]:
        """Push Docker image to Artifact Registry."""
        try:
            # Configure Docker authentication for Artifact Registry
            region = image_tag.split("-docker")[0]
            auth_cmd = f"gcloud auth configure-docker {region}-docker.pkg.dev"
            await self._run_command(auth_cmd)

            # Push image
            push_cmd = f"docker push {image_tag}"

            self.logger.info(f"Pushing Docker image: {push_cmd}")

            result = await self._run_command(push_cmd)

            if result["returncode"] == 0:
                return {"success": True}
            else:
                return {"success": False, "error": result["stderr"]}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _deploy_to_cloud_run(
        self,
        project_id: str,
        service_name: str,
        image_tag: str,
        gcp_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Deploy to Cloud Run."""
        try:
            backend_config = gcp_config.get("backend", {})
            region = gcp_config.get("region", "us-central1")

            # Build Cloud Run deploy command
            deploy_cmd = [
                "gcloud run deploy",
                service_name,
                f"--image={image_tag}",
                f"--region={region}",
                f"--project={project_id}",
                f"--platform=managed",
                f"--port={backend_config.get('container_port', 8080)}",
                f"--memory={backend_config.get('memory', '1Gi')}",
                f"--cpu={backend_config.get('cpu', '1')}",
                f"--min-instances={backend_config.get('min_instances', 0)}",
                f"--max-instances={backend_config.get('max_instances', 10)}",
                f"--timeout={backend_config.get('timeout', 300)}",
            ]

            # Add environment variables
            env_vars = backend_config.get("env_vars", {})
            if env_vars:
                env_string = ",".join([f"{k}={v}" for k, v in env_vars.items()])
                deploy_cmd.append(f"--set-env-vars={env_string}")

            # Allow unauthenticated access if configured
            if backend_config.get("allow_unauthenticated", True):
                deploy_cmd.append("--allow-unauthenticated")

            full_cmd = " ".join(deploy_cmd)

            self.logger.info(f"Deploying to Cloud Run: {full_cmd}")

            result = await self._run_command(full_cmd)

            if result["returncode"] == 0:
                # Extract service URL from output
                service_url = await self._get_service_url(project_id, service_name, region)

                return {
                    "success": True,
                    "service_url": service_url,
                }
            else:
                return {"success": False, "error": result["stderr"]}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _get_service_url(
        self, project_id: str, service_name: str, region: str
    ) -> str:
        """Get Cloud Run service URL."""
        try:
            cmd = (
                f"gcloud run services describe {service_name} "
                f"--region={region} "
                f"--project={project_id} "
                f"--format='value(status.url)'"
            )

            result = await self._run_command(cmd)

            if result["returncode"] == 0:
                return result["stdout"].strip()

        except Exception as e:
            self.logger.warning(f"Could not get service URL: {str(e)}")

        return f"https://{service_name}-<hash>-{region}.run.app"

    async def _update_cors_configuration(
        self, backend_path: Path, frontend_url: str
    ) -> Dict[str, Any]:
        """Update CORS configuration in backend source to allow the frontend origin."""
        try:
            src_java = backend_path / "src" / "main" / "java"
            if not src_java.exists():
                return {"success": False, "error": "No Java source directory found"}

            files_updated = 0

            for java_file in src_java.rglob("*.java"):
                content = java_file.read_text()

                if ".allowedOrigins(" not in content and "@CrossOrigin" not in content:
                    continue

                if frontend_url in content:
                    self.logger.info(f"CORS already configured in {java_file.name}")
                    files_updated += 1
                    continue

                updated = content

                # Handle .allowedOrigins("url1", "url2") pattern
                pattern = r'(\.allowedOrigins\()([^)]+)(\))'
                match = re.search(pattern, updated)
                if match:
                    origins_str = match.group(2).rstrip()
                    new_origins = f'{origins_str}, "{frontend_url}"'
                    updated = updated[:match.start(2)] + new_origins + updated[match.end(2):]

                # Handle @CrossOrigin(origins = {"url1", "url2"}) pattern
                pattern = r'(@CrossOrigin\(origins\s*=\s*\{)([^}]+)(\})'
                match = re.search(pattern, updated)
                if match:
                    origins_str = match.group(2).rstrip()
                    new_origins = f'{origins_str}, "{frontend_url}"'
                    updated = updated[:match.start(2)] + new_origins + updated[match.end(2):]

                # Handle @CrossOrigin(origins = "url") single origin pattern
                pattern = r'(@CrossOrigin\(origins\s*=\s*)"([^"]+)"'
                match = re.search(pattern, updated)
                if match and "{" not in match.group(0):
                    original_origin = match.group(2)
                    replacement = f'{match.group(1)}{{"{original_origin}", "{frontend_url}"}}'
                    updated = updated[:match.start()] + replacement + updated[match.end():]

                if updated != content:
                    java_file.write_text(updated)
                    files_updated += 1
                    self.logger.info(f"Updated CORS in {java_file.name}")

            return {"success": True, "files_updated": files_updated}

        except Exception as e:
            self.logger.error(f"Error updating CORS configuration: {str(e)}")
            return {"success": False, "error": str(e)}

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
