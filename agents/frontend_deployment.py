"""
Frontend Deployment Agent

Deploys React application to Firebase Hosting.
"""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict

from .base_agent import AgentResult, AgentStatus, BaseAgent, Event, EventType


class FrontendDeploymentAgent(BaseAgent):
    """
    Frontend Deployment agent that deploys React to Firebase Hosting.

    Responsibilities:
    - Detect React build configuration
    - Update API endpoint to Cloud Run URL
    - Build React production bundle
    - Deploy to Firebase Hosting
    - Configure custom domain if provided
    """

    def __init__(self, event_bus, config: Dict[str, Any], claude_api_key: str):
        super().__init__(
            name="FrontendDeployment",
            event_bus=event_bus,
            config=config,
            claude_api_key=claude_api_key,
        )

    async def _execute_impl(self) -> AgentResult:
        """Execute frontend deployment."""
        self.logger.info("Starting frontend deployment")

        # Get backend deployment information
        backend_events = self.event_bus.get_history(EventType.BACKEND_DEPLOYED)
        if not backend_events:
            return AgentResult(
                status=AgentStatus.FAILED,
                data={},
                errors=["Backend not deployed. Deploy backend first to get API URL."],
            )

        backend_data = backend_events[-1].data
        backend_url = backend_data.get("service_url")

        if not backend_url:
            return AgentResult(
                status=AgentStatus.FAILED,
                data={},
                errors=["Backend service URL not available"],
            )

        # Get infrastructure information
        infra_events = self.event_bus.get_history(EventType.INFRASTRUCTURE_READY)
        infra_data = infra_events[-1].data if infra_events else {}

        warnings = []
        errors = []
        deployment_result = {
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

            # Configure environment variables with backend URL
            self.logger.info("Configuring environment variables")
            env_result = await self._configure_environment(frontend_path, backend_url)
            if env_result["success"]:
                deployment_result["env_configured"] = True
            else:
                warnings.append(f"Environment configuration: {env_result.get('error')}")

            # Install dependencies
            self.logger.info("Installing dependencies")
            install_result = await self._install_dependencies(frontend_path)
            if not install_result["success"]:
                errors.append(f"Dependency installation failed: {install_result.get('error')}")
                return AgentResult(
                    status=AgentStatus.FAILED,
                    data=deployment_result,
                    errors=errors,
                )

            # Build React app
            self.logger.info("Building React production bundle")
            build_result = await self._build_react_app(frontend_path)
            if build_result["success"]:
                deployment_result["build_completed"] = True
            else:
                errors.append(f"Build failed: {build_result.get('error')}")
                return AgentResult(
                    status=AgentStatus.FAILED,
                    data=deployment_result,
                    errors=errors,
                )

            # Initialize Firebase
            self.logger.info("Initializing Firebase")
            firebase_result = await self._initialize_firebase(frontend_path)
            if firebase_result["success"]:
                deployment_result["firebase_initialized"] = True
            else:
                errors.append(f"Firebase initialization failed: {firebase_result.get('error')}")
                return AgentResult(
                    status=AgentStatus.FAILED,
                    data=deployment_result,
                    errors=errors,
                )

            # Deploy to Firebase Hosting
            self.logger.info("Deploying to Firebase Hosting")
            deploy_result = await self._deploy_to_firebase(frontend_path)
            if deploy_result["success"]:
                deployment_result["deployed"] = True
                deployment_result["hosting_url"] = deploy_result["hosting_url"]
            else:
                errors.append(f"Firebase deployment failed: {deploy_result.get('error')}")
                return AgentResult(
                    status=AgentStatus.FAILED,
                    data=deployment_result,
                    errors=errors,
                )

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

    async def _configure_environment(
        self, frontend_path: Path, backend_url: str
    ) -> Dict[str, Any]:
        """Configure environment variables for React app."""
        try:
            # Create or update .env.production file
            env_file = frontend_path / ".env.production"

            env_content = f"""# Auto-generated by Cloudify Migration
VITE_API_URL={backend_url}
VITE_BACKEND_URL={backend_url}
"""

            env_file.write_text(env_content)

            self.logger.info(f"Environment file created: {env_file}")

            return {"success": True, "env_file": str(env_file)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _install_dependencies(self, frontend_path: Path) -> Dict[str, Any]:
        """Install npm dependencies."""
        try:
            # Check if package-lock.json exists
            if (frontend_path / "package-lock.json").exists():
                cmd = "npm ci"
            else:
                cmd = "npm install"

            result = await self._run_command(cmd, cwd=frontend_path)

            if result["returncode"] == 0:
                return {"success": True}
            else:
                return {"success": False, "error": result["stderr"]}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _build_react_app(self, frontend_path: Path) -> Dict[str, Any]:
        """Build React production bundle."""
        try:
            cmd = "npm run build"

            result = await self._run_command(cmd, cwd=frontend_path)

            if result["returncode"] == 0:
                # Check if build directory exists
                build_dir = frontend_path / "dist"  # Vite uses 'dist'
                if not build_dir.exists():
                    build_dir = frontend_path / "build"  # CRA uses 'build'

                if build_dir.exists():
                    return {"success": True, "build_dir": str(build_dir)}
                else:
                    return {"success": False, "error": "Build directory not found"}
            else:
                return {"success": False, "error": result["stderr"]}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _initialize_firebase(self, frontend_path: Path) -> Dict[str, Any]:
        """Initialize Firebase configuration."""
        try:
            gcp_config = self.config.get("gcp", {})
            project_id = gcp_config.get("project_id")

            # Check if firebase.json already exists
            firebase_config_file = frontend_path / "firebase.json"

            if not firebase_config_file.exists():
                # Create firebase.json
                firebase_config = {
                    "hosting": {
                        "public": "dist",  # Vite default
                        "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
                        "rewrites": [
                            {
                                "source": "**",
                                "destination": "/index.html"
                            }
                        ]
                    }
                }

                # Check if build directory is 'build' instead of 'dist'
                if (frontend_path / "build").exists():
                    firebase_config["hosting"]["public"] = "build"

                firebase_config_file.write_text(json.dumps(firebase_config, indent=2))

                self.logger.info(f"Firebase config created: {firebase_config_file}")

            # Create .firebaserc
            firebaserc_file = frontend_path / ".firebaserc"
            if not firebaserc_file.exists():
                firebaserc_config = {
                    "projects": {
                        "default": project_id
                    }
                }

                firebaserc_file.write_text(json.dumps(firebaserc_config, indent=2))

            return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _deploy_to_firebase(self, frontend_path: Path) -> Dict[str, Any]:
        """Deploy to Firebase Hosting."""
        try:
            gcp_config = self.config.get("gcp", {})
            project_id = gcp_config.get("project_id")

            # Login to Firebase (non-interactive)
            # Note: This assumes the user is already authenticated with gcloud
            # which shares credentials with Firebase

            # Deploy
            deploy_cmd = f"firebase deploy --only hosting --project={project_id}"

            result = await self._run_command(deploy_cmd, cwd=frontend_path)

            if result["returncode"] == 0:
                # Extract hosting URL
                hosting_url = f"https://{project_id}.web.app"

                # Try to extract actual URL from output
                if "Hosting URL:" in result["stdout"]:
                    for line in result["stdout"].split("\n"):
                        if "Hosting URL:" in line:
                            hosting_url = line.split("Hosting URL:")[-1].strip()
                            break

                return {
                    "success": True,
                    "hosting_url": hosting_url,
                }
            else:
                return {"success": False, "error": result["stderr"]}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _run_command(
        self, command: str, cwd: Path = None
    ) -> Dict[str, Any]:
        """Run shell command asynchronously."""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(cwd) if cwd else None,
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
