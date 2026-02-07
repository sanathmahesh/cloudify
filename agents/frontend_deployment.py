"""
Frontend Deployment Agent — Powered by Dedalus SDK

Deploys React application to Firebase Hosting using:
- FAST model (GPT-4.1-mini) for simple build/deploy operations
- Local tools for npm, build, and Firebase deployment
- Dedalus tool calling for all deployment steps
"""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict

from .base_agent import AgentResult, AgentStatus, BaseAgent, Event, EventType, ModelRole
from .dedalus_tools import (
    FRONTEND_DEPLOYMENT_TOOLS,
    build_frontend,
    configure_frontend_env,
    deploy_to_firebase,
    install_npm_dependencies,
)


class FrontendDeploymentAgent(BaseAgent):
    """
    Frontend Deployment agent powered by Dedalus SDK.

    Uses the FAST model for simple build/deploy operations — this is
    intentionally a cheaper/faster model because frontend deployment
    is straightforward compared to code analysis or Dockerfile generation.
    """

    def __init__(self, event_bus, config: Dict[str, Any], dedalus_api_key: str):
        super().__init__(
            name="FrontendDeployment",
            event_bus=event_bus,
            config=config,
            dedalus_api_key=dedalus_api_key,
        )

    async def _execute_impl(self) -> AgentResult:
        """Execute frontend deployment with Dedalus FAST model and tools."""
        self.logger.info("Starting frontend deployment with Dedalus FAST model")

        # Wait for backend deployment
        self.logger.info("Waiting for Backend Deployment to complete...")
        max_retries = 60
        backend_data = None

        for i in range(max_retries):
            backend_events = self.event_bus.get_history(EventType.BACKEND_DEPLOYED)
            if backend_events:
                backend_data = backend_events[-1].data
                self.logger.info("Backend deployment detected!")
                break
            if i % 6 == 0:
                self.logger.info(f"Still waiting for backend... ({i * 10}s elapsed)")
            await asyncio.sleep(10)

        if not backend_data:
            return AgentResult(
                status=AgentStatus.FAILED,
                data={},
                errors=["Timed out waiting for Backend Deployment (10 minutes)."],
            )

        backend_url = backend_data.get("service_url")
        if not backend_url:
            return AgentResult(
                status=AgentStatus.FAILED,
                data={},
                errors=["Backend service URL not available"],
            )

        warnings: list[str] = []
        errors: list[str] = []
        deployment_result: Dict[str, Any] = {
            "env_configured": False,
            "build_completed": False,
            "firebase_initialized": False,
            "deployed": False,
            "hosting_url": None,
        }

        try:
            source_path = Path(self.config["source"]["path"])
            frontend_path = source_path / self.config["source"]["frontend"]["path"]

            if not frontend_path.exists():
                return AgentResult(
                    status=AgentStatus.FAILED,
                    data={},
                    errors=[f"Frontend path not found: {frontend_path}"],
                )

            # Step 1: Configure environment (tool call)
            self.logger.info("Configuring environment variables")
            env_raw = await configure_frontend_env(str(frontend_path), backend_url)
            env_data = json.loads(env_raw)
            if env_data.get("success"):
                deployment_result["env_configured"] = True
            else:
                warnings.append(f"Environment configuration: {env_data.get('error')}")

            # Step 2: Install dependencies (tool call)
            self.logger.info("Installing dependencies")
            install_raw = await install_npm_dependencies(str(frontend_path))
            install_data = json.loads(install_raw)
            if not install_data.get("success"):
                errors.append(f"Dependency installation failed: {install_data.get('error')}")
                return AgentResult(status=AgentStatus.FAILED, data=deployment_result, errors=errors)

            # Step 3: Build React app (tool call)
            self.logger.info("Building React production bundle")
            build_raw = await build_frontend(str(frontend_path))
            build_data = json.loads(build_raw)
            if build_data.get("success"):
                deployment_result["build_completed"] = True
            else:
                errors.append(f"Build failed: {build_data.get('error')}")
                return AgentResult(status=AgentStatus.FAILED, data=deployment_result, errors=errors)

            # Step 4: Deploy to Firebase (tool call)
            self.logger.info("Deploying to Firebase Hosting")
            gcp_config = self.config.get("gcp", {})
            project_id = gcp_config.get("project_id")
            site_name = gcp_config.get("frontend", {}).get("site_name", project_id)

            deploy_raw = await deploy_to_firebase(str(frontend_path), project_id, site_name)
            deploy_data = json.loads(deploy_raw)
            if deploy_data.get("success"):
                deployment_result["firebase_initialized"] = True
                deployment_result["deployed"] = True
                deployment_result["hosting_url"] = deploy_data["hosting_url"]
            else:
                errors.append(f"Firebase deployment failed: {deploy_data.get('error')}")
                return AgentResult(status=AgentStatus.FAILED, data=deployment_result, errors=errors)

            # Step 5: Use FAST model for quick deployment verification
            try:
                verification = await self.run_with_dedalus(
                    prompt=(
                        f"Frontend deployed to {deployment_result['hosting_url']} "
                        f"with backend at {backend_url}. "
                        f"Provide 1-2 quick post-deployment checks to verify everything works."
                    ),
                    model=ModelRole.FAST.value,
                    instructions="You are a deployment verification expert. Be very concise.",
                    max_steps=1,
                )
                deployment_result["verification_tips"] = verification
            except Exception as e:
                self.logger.warning(f"Verification tips skipped: {e}")

            # Publish frontend deployed event
            await self.event_bus.publish(Event(
                event_type=EventType.FRONTEND_DEPLOYED,
                source_agent=self.name,
                data={
                    "hosting_url": deployment_result["hosting_url"],
                    "backend_url": backend_url,
                },
            ))

            return AgentResult(
                status=AgentStatus.SUCCESS,
                data=deployment_result,
                warnings=warnings,
            )

        except Exception as e:
            self.logger.error(f"Frontend deployment error: {str(e)}", exc_info=True)
            return AgentResult(
                status=AgentStatus.FAILED,
                data=deployment_result,
                errors=[str(e)],
            )
