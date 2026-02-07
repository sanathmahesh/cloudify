"""
Backend Deployment Agent — Powered by Dedalus SDK

Deploys Spring Boot application to Cloud Run using:
- CODE_GENERATION model (Claude Opus) for Dockerfile generation
- FAST model (GPT-4.1-mini) for error triage
- Local tools for Docker build, push, and Cloud Run deploy
- Policy-based escalation: fast model first, escalate to reasoning on failure
"""

import json
from pathlib import Path
from typing import Any, Dict

from .base_agent import AgentResult, AgentStatus, BaseAgent, Event, EventType, ModelRole
from .dedalus_tools import (
    BACKEND_DEPLOYMENT_TOOLS,
    build_docker_image,
    deploy_to_cloud_run,
    push_docker_image,
    update_cors_origins,
    write_dockerfile,
)


def _escalation_policy(state: Any) -> dict:
    """Dynamic model routing policy: escalate from fast to reasoning model on complex steps.

    If the agent has already used more than 3 steps (meaning it's struggling),
    escalate to the full reasoning model for better problem-solving.
    """
    steps = getattr(state, "steps_used", 0)
    if steps > 3:
        return {"model": ModelRole.REASONING.value}
    return {"model": ModelRole.CODE_GENERATION.value}


class BackendDeploymentAgent(BaseAgent):
    """
    Backend Deployment agent powered by Dedalus SDK.

    Uses CODE_GENERATION model for Dockerfile creation and FAST model
    for simple deployment operations, with escalation policy.
    """

    def __init__(self, event_bus, config: Dict[str, Any], dedalus_api_key: str):
        super().__init__(
            name="BackendDeployment",
            event_bus=event_bus,
            config=config,
            dedalus_api_key=dedalus_api_key,
        )

    async def _execute_impl(self) -> AgentResult:
        """Execute backend deployment with model handoffs and tool calling."""
        self.logger.info("Starting backend deployment with Dedalus CODE_GENERATION model")

        # Get infrastructure information
        infra_events = self.event_bus.get_history(EventType.INFRASTRUCTURE_READY)
        if not infra_events:
            return AgentResult(
                status=AgentStatus.FAILED,
                data={},
                errors=["Infrastructure not provisioned. Run infrastructure agent first."],
            )

        infra_data = infra_events[-1].data
        registry_url = infra_data.get("artifact_registry", {}).get("repository_url")
        if not registry_url:
            return AgentResult(
                status=AgentStatus.FAILED,
                data={},
                errors=["Artifact Registry repository URL not found"],
            )

        analysis_events = self.event_bus.get_history(EventType.ANALYSIS_COMPLETE)
        analysis_data = analysis_events[-1].data if analysis_events else {}

        warnings: list[str] = []
        errors: list[str] = []
        deployment_result: Dict[str, Any] = {
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

            # Step 1: Generate Dockerfile using CODE_GENERATION model
            self.logger.info("Generating Dockerfile with Dedalus CODE_GENERATION model")
            dockerfile_content = await self._generate_dockerfile(analysis_data)
            write_raw = await write_dockerfile(str(backend_path), dockerfile_content)
            write_data = json.loads(write_raw)
            if write_data.get("success"):
                deployment_result["dockerfile_created"] = True
            else:
                errors.append(f"Dockerfile generation failed: {write_data.get('error')}")
                return AgentResult(status=AgentStatus.FAILED, data=deployment_result, errors=errors)

            # Step 2: Update CORS configuration (tool call)
            site_name = self.config.get("gcp", {}).get("frontend", {}).get("site_name")
            if site_name:
                frontend_url = f"https://{site_name}.web.app"
                self.logger.info(f"Updating CORS for frontend: {frontend_url}")
                cors_raw = await update_cors_origins(str(backend_path), frontend_url)
                cors_data = json.loads(cors_raw)
                if cors_data.get("success"):
                    self.logger.info(f"CORS updated: {cors_data.get('files_updated', 0)} file(s)")
                else:
                    warnings.append(f"CORS update: {cors_data.get('error')}")

            # Step 3: Build Docker image (tool call)
            gcp_config = self.config.get("gcp", {})
            project_id = gcp_config.get("project_id")
            service_name = gcp_config.get("backend", {}).get("service_name", "app-backend")
            image_tag = f"{registry_url}/{service_name}:latest"

            self.logger.info(f"Building Docker image: {image_tag}")
            build_raw = await build_docker_image(str(backend_path), image_tag)
            build_data = json.loads(build_raw)
            if build_data.get("success"):
                deployment_result["image_built"] = True
            else:
                errors.append(f"Docker build failed: {build_data.get('error')}")
                return AgentResult(status=AgentStatus.FAILED, data=deployment_result, errors=errors)

            # Step 4: Push image (tool call)
            self.logger.info("Pushing image to Artifact Registry")
            push_raw = await push_docker_image(image_tag)
            push_data = json.loads(push_raw)
            if push_data.get("success"):
                deployment_result["image_pushed"] = True
            else:
                errors.append(f"Docker push failed: {push_data.get('error')}")
                return AgentResult(status=AgentStatus.FAILED, data=deployment_result, errors=errors)

            # Step 5: Deploy to Cloud Run (tool call)
            self.logger.info("Deploying to Cloud Run")
            backend_config = gcp_config.get("backend", {})
            deploy_raw = await deploy_to_cloud_run(
                project_id=project_id,
                region=gcp_config.get("region", "us-central1"),
                service_name=service_name,
                image_tag=image_tag,
                port=backend_config.get("container_port", 8080),
                memory=backend_config.get("memory", "1Gi"),
                cpu=backend_config.get("cpu", "1"),
                min_instances=backend_config.get("min_instances", 0),
                max_instances=backend_config.get("max_instances", 10),
                env_vars=backend_config.get("env_vars", {}),
                allow_unauthenticated=backend_config.get("allow_unauthenticated", True),
            )
            deploy_data = json.loads(deploy_raw)
            if deploy_data.get("success"):
                deployment_result["service_deployed"] = True
                deployment_result["service_url"] = deploy_data["service_url"]
            else:
                errors.append(f"Cloud Run deployment failed: {deploy_data.get('error')}")
                return AgentResult(status=AgentStatus.FAILED, data=deployment_result, errors=errors)

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

    async def _generate_dockerfile(self, analysis_data: Dict[str, Any]) -> str:
        """Generate optimized Dockerfile using Dedalus CODE_GENERATION model.

        Uses Claude Opus for code generation with escalation policy:
        if the model struggles, it escalates to the reasoning model.
        """
        backend_analysis = analysis_data.get("backend", {})
        build_tool = backend_analysis.get("build_tool", "maven")
        java_version = backend_analysis.get("java_version", "21")
        spring_version = backend_analysis.get("spring_boot_version", "3.x")

        prompt = f"""Generate an optimized Dockerfile for a Spring Boot application:
- Build tool: {build_tool}
- Java version: {java_version}
- Spring Boot version: {spring_version}

Requirements:
1. Multi-stage build to minimize image size
2. Use appropriate base images
3. Optimize layer caching
4. Non-root user for security
5. Health check endpoint
6. Expose port 8080

Provide ONLY the Dockerfile content, no explanations or markdown fences."""

        response = await self.run_with_dedalus(
            prompt=prompt,
            model=ModelRole.CODE_GENERATION.value,
            tools=BACKEND_DEPLOYMENT_TOOLS,
            instructions="You are a Docker expert specializing in Java applications. Output only Dockerfile content.",
            max_steps=3,
            policy=_escalation_policy,
        )

        return response.strip()
