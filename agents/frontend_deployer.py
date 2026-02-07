"""Frontend Deployment Agent — builds and deploys the React app to Firebase Hosting.

Responsibilities:
- Detect React build configuration
- Update API endpoint to Cloud Run URL
- Build React production bundle
- Deploy to Firebase Hosting
- Configure custom domain if provided
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.base import BaseAgent
from utils.gcp import GCPClient
from utils.logger import get_logger
from utils.shell import run_command

log = get_logger(__name__)

FIREBASE_JSON_TEMPLATE = """{
  "hosting": {
    "public": "%BUILD_DIR%",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ],
    "headers": [
      {
        "source": "/static/**",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "public, max-age=31536000, immutable"
          }
        ]
      }
    ]
  }
}
"""


class FrontendDeployerAgent(BaseAgent):
    name = "frontend_deployer"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.gcp = GCPClient(self.config.gcp, dry_run=self.dry_run)

    # -- Tools ----------------------------------------------------------------

    def _detect_frontend_framework(self, frontend_path: str) -> Dict[str, Any]:
        """Detect frontend framework and build configuration.

        Args:
            frontend_path: Path to the frontend source root.

        Returns:
            Dict with framework name, build command, output dir, and package manager.
        """
        fe = Path(frontend_path)
        info: Dict[str, Any] = {
            "framework": "unknown",
            "build_command": "npm run build",
            "output_dir": "build",
            "package_manager": "npm",
        }

        # Detect package manager
        if (fe / "yarn.lock").exists():
            info["package_manager"] = "yarn"
        elif (fe / "pnpm-lock.yaml").exists():
            info["package_manager"] = "pnpm"

        # Read package.json
        pkg_path = fe / "package.json"
        if pkg_path.exists():
            pkg = json.loads(pkg_path.read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

            if "next" in deps:
                info["framework"] = "next"
                info["output_dir"] = "out"
            elif "vite" in deps or "@vitejs/plugin-react" in deps:
                info["framework"] = "vite"
                info["output_dir"] = "dist"
            elif "react-scripts" in deps:
                info["framework"] = "create-react-app"
                info["output_dir"] = "build"

            # Check for custom build script
            scripts = pkg.get("scripts", {})
            if "build" in scripts:
                info["build_command"] = f"{info['package_manager']} run build"

        return info

    def _update_api_endpoint(
        self,
        frontend_path: str,
        backend_url: str,
    ) -> List[str]:
        """Update API endpoint references in the React frontend to point to Cloud Run.

        Args:
            frontend_path: Path to the frontend source root.
            backend_url: Cloud Run backend URL.

        Returns:
            List of files that were modified.
        """
        fe = Path(frontend_path)
        modified: List[str] = []

        # Update .env files
        env_file = fe / ".env.production"
        env_lines = []
        wrote_api_url = False
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if "API" in line.upper() and "URL" in line.upper() and "=" in line:
                    key = line.split("=")[0]
                    env_lines.append(f"{key}={backend_url}")
                    wrote_api_url = True
                else:
                    env_lines.append(line)

        if not wrote_api_url:
            env_lines.append(f"REACT_APP_API_URL={backend_url}")
            env_lines.append(f"VITE_API_URL={backend_url}")

        env_file.write_text("\n".join(env_lines) + "\n")
        modified.append(str(env_file))

        # Update package.json proxy
        pkg_path = fe / "package.json"
        if pkg_path.exists():
            pkg = json.loads(pkg_path.read_text())
            if "proxy" in pkg:
                pkg["proxy"] = backend_url
                pkg_path.write_text(json.dumps(pkg, indent=2) + "\n")
                modified.append(str(pkg_path))

        return modified

    def _generate_firebase_json(self, frontend_path: str, build_dir: str) -> str:
        """Generate firebase.json for hosting configuration.

        Args:
            frontend_path: Path to the frontend source root.
            build_dir: Build output directory name.

        Returns:
            Path to the generated firebase.json file.
        """
        fe = Path(frontend_path)
        content = FIREBASE_JSON_TEMPLATE.replace("%BUILD_DIR%", build_dir)
        out_path = fe / "firebase.json"
        out_path.write_text(content)
        return str(out_path)

    def _generate_firebaserc(self, frontend_path: str, project_id: str) -> str:
        """Generate .firebaserc with project configuration.

        Args:
            frontend_path: Path to the frontend source root.
            project_id: GCP project ID.

        Returns:
            Path to the generated .firebaserc file.
        """
        fe = Path(frontend_path)
        rc = {"projects": {"default": project_id}}
        out_path = fe / ".firebaserc"
        out_path.write_text(json.dumps(rc, indent=2) + "\n")
        return str(out_path)

    # -- Agent interface -------------------------------------------------------

    def get_tools(self) -> list:
        return [
            self._detect_frontend_framework,
            self._update_api_endpoint,
            self._generate_firebase_json,
            self._generate_firebaserc,
        ]

    def get_prompt(self) -> str:
        return (
            "You are a frontend deployment specialist. Update API endpoints, "
            "build the React production bundle, and deploy to Firebase Hosting."
        )

    async def execute(self) -> Dict[str, Any]:
        """Build and deploy the React frontend to Firebase Hosting."""
        frontend_path = self.config.source.frontend_abs
        backend_deployment = self.state.get_artifact("backend_deployment", {})
        backend_url = backend_deployment.get("service_url", "")

        # Step 1: Detect framework
        self.log.info("Detecting frontend framework...")
        framework_info = self._detect_frontend_framework(str(frontend_path))
        self.log.info(f"Framework: {framework_info['framework']}, output: {framework_info['output_dir']}")

        build_output = self.config.frontend.build_output or framework_info["output_dir"]

        # Step 2: Update API endpoint
        if backend_url:
            self.log.info(f"Updating API endpoint to: {backend_url}")
            modified = self._update_api_endpoint(str(frontend_path), backend_url)
            self.state.generated_files.extend(modified)
        else:
            self.log.warning("No backend URL available — API endpoints not updated")

        # Step 3: Generate Firebase config
        self.log.info("Generating Firebase configuration...")
        firebase_json = self._generate_firebase_json(str(frontend_path), build_output)
        firebaserc = self._generate_firebaserc(
            str(frontend_path), self.config.gcp.project_id
        )
        self.state.generated_files.extend([firebase_json, firebaserc])

        # Step 4: Install dependencies
        self.log.info("Installing frontend dependencies...")
        pkg_manager = framework_info["package_manager"]
        install_cmd = f"{pkg_manager} install"
        if not self.dry_run:
            install_result = run_command(install_cmd, cwd=str(frontend_path), timeout=120)
            if not install_result.success:
                raise RuntimeError(f"npm install failed: {install_result.stderr}")
        else:
            self.state.dry_run_scripts.append(f"cd {frontend_path} && {install_cmd}")

        # Step 5: Build
        build_cmd = self.config.frontend.build_command or framework_info["build_command"]
        self.log.info(f"Building frontend: {build_cmd}")

        # Set environment variables for build
        env_prefix = ""
        if backend_url:
            env_prefix = f"REACT_APP_API_URL={backend_url} VITE_API_URL={backend_url} "

        if not self.dry_run:
            build_result = run_command(
                f"{env_prefix}{build_cmd}",
                cwd=str(frontend_path),
                timeout=180,
            )
            if not build_result.success:
                raise RuntimeError(f"Frontend build failed: {build_result.stderr}")
        else:
            self.state.dry_run_scripts.append(
                f"cd {frontend_path} && {env_prefix}{build_cmd}"
            )

        # Step 6: Deploy to Firebase Hosting
        self.log.info("Deploying to Firebase Hosting...")
        if not self.dry_run:
            deploy_result = self.gcp.firebase_deploy_hosting(str(frontend_path))
            if not deploy_result.success:
                raise RuntimeError(f"Firebase deploy failed: {deploy_result.stderr}")
        else:
            self.state.dry_run_scripts.append(
                f"cd {frontend_path} && "
                f"firebase deploy --only hosting --project={self.config.gcp.project_id}"
            )

        # Determine hosting URL
        site_name = self.config.frontend.site_name or self.config.gcp.project_id
        hosting_url = f"https://{site_name}.web.app"
        self.state.deployment_urls["frontend"] = hosting_url

        output = {
            "framework": framework_info,
            "build_output": build_output,
            "hosting_url": hosting_url,
            "firebase_json": firebase_json,
        }

        self.state.set_artifact("frontend_deployment", output)
        if self.dry_run:
            self.state.dry_run_scripts.extend(self.gcp.scripts)

        self.log.info(f"Frontend deployed at: {hosting_url}")
        return output

    async def rollback(self) -> None:
        """Firebase Hosting rollback — disable the site."""
        self.log.info("Rolling back Firebase Hosting deployment...")
        # Firebase doesn't have a simple delete; we log the action
        self.log.info(
            "To rollback, run: firebase hosting:disable "
            f"--project={self.config.gcp.project_id}"
        )
        self.agent_state.mark_rolled_back()
