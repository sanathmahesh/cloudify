"""Code Analyzer Agent — scans the source application and produces a migration requirements report.

Responsibilities:
- Parse Spring Boot application.properties / application.yml
- Detect database configuration (H2 mode, connection URL)
- Identify REST API endpoints and CORS settings
- Analyze React app for API endpoint configurations
- Output a structured migration requirements report
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.base import BaseAgent
from utils.logger import get_logger

log = get_logger(__name__)


class CodeAnalyzerAgent(BaseAgent):
    name = "code_analyzer"

    # -- Tools exposed to the LLM --------------------------------------------

    def _scan_spring_properties(self, file_path: str) -> Dict[str, str]:
        """Read a Spring Boot properties file and return key-value pairs.

        Args:
            file_path: Absolute path to the properties file.

        Returns:
            Dictionary of property keys to values.
        """
        props: Dict[str, str] = {}
        p = Path(file_path)
        if not p.exists():
            return props
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                props[key.strip()] = value.strip()
        return props

    def _scan_yaml_config(self, file_path: str) -> str:
        """Read a YAML configuration file and return its raw content.

        Args:
            file_path: Absolute path to the YAML file.

        Returns:
            Raw YAML content as string.
        """
        p = Path(file_path)
        if not p.exists():
            return ""
        return p.read_text()

    def _find_rest_controllers(self, backend_path: str) -> List[Dict[str, Any]]:
        """Scan Java source files for REST controller annotations and extract endpoints.

        Args:
            backend_path: Path to the Spring Boot backend source root.

        Returns:
            List of dicts with controller class, base path, and method endpoints.
        """
        controllers: List[Dict[str, Any]] = []
        src_root = Path(backend_path)
        for java_file in src_root.rglob("*.java"):
            content = java_file.read_text()
            if "@RestController" not in content and "@Controller" not in content:
                continue

            controller: Dict[str, Any] = {
                "file": str(java_file),
                "class": "",
                "base_path": "",
                "endpoints": [],
            }

            # Extract class name
            class_match = re.search(r"class\s+(\w+)", content)
            if class_match:
                controller["class"] = class_match.group(1)

            # Extract base request mapping
            base_match = re.search(
                r'@RequestMapping\(["\']?([^"\')\s]+)', content
            )
            if base_match:
                controller["base_path"] = base_match.group(1)

            # Extract method-level mappings
            method_patterns = [
                (r'@GetMapping\(["\']?([^"\')\s]*)', "GET"),
                (r'@PostMapping\(["\']?([^"\')\s]*)', "POST"),
                (r'@PutMapping\(["\']?([^"\')\s]*)', "PUT"),
                (r'@DeleteMapping\(["\']?([^"\')\s]*)', "DELETE"),
                (r'@PatchMapping\(["\']?([^"\')\s]*)', "PATCH"),
            ]
            for pattern, method in method_patterns:
                for m in re.finditer(pattern, content):
                    controller["endpoints"].append(
                        {"method": method, "path": m.group(1) or "/"}
                    )

            controllers.append(controller)
        return controllers

    def _find_cors_config(self, backend_path: str) -> List[str]:
        """Scan Java files for CORS configuration annotations or beans.

        Args:
            backend_path: Path to the backend source root.

        Returns:
            List of file paths that contain CORS configuration.
        """
        cors_files: List[str] = []
        for java_file in Path(backend_path).rglob("*.java"):
            content = java_file.read_text()
            if any(
                token in content
                for token in ["@CrossOrigin", "CorsRegistry", "CorsConfiguration"]
            ):
                cors_files.append(str(java_file))
        return cors_files

    def _analyze_react_api_config(self, frontend_path: str) -> Dict[str, Any]:
        """Scan React frontend for API endpoint configuration.

        Args:
            frontend_path: Path to the React frontend root.

        Returns:
            Dict with detected API base URLs, env files, and proxy config.
        """
        result: Dict[str, Any] = {
            "api_urls": [],
            "env_files": [],
            "proxy_config": None,
            "package_json_proxy": None,
        }
        fe = Path(frontend_path)

        # Check .env files
        for env_file in fe.glob(".env*"):
            result["env_files"].append(str(env_file))
            content = env_file.read_text()
            for line in content.splitlines():
                if "API" in line.upper() and "=" in line:
                    result["api_urls"].append(line.strip())

        # Check package.json for proxy
        pkg_json = fe / "package.json"
        if pkg_json.exists():
            import json
            pkg = json.loads(pkg_json.read_text())
            if "proxy" in pkg:
                result["package_json_proxy"] = pkg["proxy"]

        # Scan JS/TS source for API base URL patterns
        for ext in ("*.js", "*.jsx", "*.ts", "*.tsx"):
            for src_file in fe.rglob(ext):
                try:
                    content = src_file.read_text()
                except (UnicodeDecodeError, PermissionError):
                    continue
                # Common patterns: axios.create({ baseURL: ... }), fetch("http://...
                url_matches = re.findall(
                    r'(?:baseURL|BASE_URL|API_URL|apiUrl|api_url)\s*[:=]\s*["\']([^"\']+)',
                    content,
                )
                for url in url_matches:
                    if url not in result["api_urls"]:
                        result["api_urls"].append(url)

        return result

    def _detect_build_system(self, backend_path: str) -> Dict[str, Any]:
        """Detect Maven or Gradle build system.

        Args:
            backend_path: Path to the backend source root.

        Returns:
            Dict with build_tool, wrapper presence, and java version.
        """
        bp = Path(backend_path)
        info: Dict[str, Any] = {"build_tool": "unknown", "wrapper": False, "java_version": None}
        if (bp / "pom.xml").exists():
            info["build_tool"] = "maven"
            info["wrapper"] = (bp / "mvnw").exists()
            # Try to extract Java version from pom.xml
            pom = (bp / "pom.xml").read_text()
            jv = re.search(r"<java\.version>(\d+)</java\.version>", pom)
            if jv:
                info["java_version"] = jv.group(1)
        elif (bp / "build.gradle").exists() or (bp / "build.gradle.kts").exists():
            info["build_tool"] = "gradle"
            info["wrapper"] = (bp / "gradlew").exists()
        return info

    # -- Agent interface -------------------------------------------------------

    def get_tools(self) -> list:
        return [
            self._scan_spring_properties,
            self._scan_yaml_config,
            self._find_rest_controllers,
            self._find_cors_config,
            self._analyze_react_api_config,
            self._detect_build_system,
        ]

    def get_prompt(self) -> str:
        return (
            "You are a code analysis agent specializing in Spring Boot + React applications. "
            "Analyze the source application and produce a comprehensive migration requirements report. "
            "Use the provided tools to scan the backend and frontend. Identify:\n"
            "1. Database configuration (H2 in-memory vs file-based, connection URL)\n"
            "2. All REST API endpoints with their HTTP methods\n"
            "3. CORS configuration\n"
            "4. React API endpoint configuration and proxy settings\n"
            "5. Build system (Maven/Gradle) and Java version\n"
            "Return a structured JSON report with all findings."
        )

    async def execute(self) -> Dict[str, Any]:
        """Run code analysis on the source application."""
        backend_path = str(self.config.source.backend_abs)
        frontend_path = str(self.config.source.frontend_abs)

        self.log.info(f"Analyzing backend at: {backend_path}")
        self.log.info(f"Analyzing frontend at: {frontend_path}")

        # Run all scans
        build_info = self._detect_build_system(backend_path)

        # Find Spring properties
        props: Dict[str, str] = {}
        for name in ("application.properties", "application.yml", "application.yaml"):
            for pf in Path(backend_path).rglob(name):
                if "application.properties" in name:
                    props.update(self._scan_spring_properties(str(pf)))
                else:
                    raw_yaml = self._scan_yaml_config(str(pf))
                    if raw_yaml:
                        props["_raw_yaml"] = raw_yaml
                break

        # Database detection
        db_info: Dict[str, Any] = {"type": "unknown", "url": "", "mode": ""}
        db_url = props.get("spring.datasource.url", "")
        if "h2" in db_url.lower():
            db_info["type"] = "h2"
            db_info["url"] = db_url
            db_info["mode"] = "in-memory" if "mem:" in db_url else "file-based"
        elif "mysql" in db_url.lower():
            db_info["type"] = "mysql"
            db_info["url"] = db_url
        elif "postgres" in db_url.lower():
            db_info["type"] = "postgresql"
            db_info["url"] = db_url

        # REST endpoints
        controllers = self._find_rest_controllers(backend_path)

        # CORS
        cors_files = self._find_cors_config(backend_path)

        # React API config
        react_config = self._analyze_react_api_config(frontend_path)

        # Use LLM to generate a migration recommendations summary
        analysis_context = (
            f"Build system: {build_info}\n"
            f"Database: {db_info}\n"
            f"Spring properties: {dict(list(props.items())[:20])}\n"
            f"Controllers found: {len(controllers)}\n"
            f"CORS config files: {cors_files}\n"
            f"React API config: {react_config}\n"
        )

        recommendations = await self.ask_llm(
            f"Based on this application analysis, provide 3-5 key migration "
            f"recommendations for deploying to GCP Cloud Run + Firebase Hosting. "
            f"Be concise.\n\n{analysis_context}",
        )

        report = {
            "build_system": build_info,
            "database": db_info,
            "spring_properties": props,
            "controllers": controllers,
            "cors_files": cors_files,
            "react_config": react_config,
            "recommendations": recommendations,
        }

        self.state.set_artifact("analysis_report", report)
        self.log.info(
            f"Analysis complete: {len(controllers)} controllers, "
            f"DB type={db_info['type']}, build={build_info['build_tool']}"
        )
        return report
