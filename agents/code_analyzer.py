"""
Code Analyzer Agent

Analyzes the source application to extract configuration and requirements.
"""

import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_agent import AgentResult, AgentStatus, BaseAgent, Event, EventType


class CodeAnalyzerAgent(BaseAgent):
    """
    Code Analyzer agent that scans and analyzes the source application.

    Responsibilities:
    - Scan Spring Boot application.properties/application.yml
    - Detect database configuration (H2, MySQL, PostgreSQL)
    - Identify API endpoints and CORS settings
    - Analyze React app for API endpoint configurations
    - Extract build tool information (Maven/Gradle, npm/yarn)
    - Output migration requirements report
    """

    def __init__(self, event_bus, config: Dict[str, Any], claude_api_key: str):
        super().__init__(
            name="CodeAnalyzer",
            event_bus=event_bus,
            config=config,
            claude_api_key=claude_api_key,
        )

    async def _execute_impl(self) -> AgentResult:
        """Execute code analysis."""
        self.logger.info("Starting code analysis")

        source_path = Path(self.config["source"]["path"])

        if not source_path.exists():
            return AgentResult(
                status=AgentStatus.FAILED,
                data={},
                errors=[f"Source path does not exist: {source_path}"],
            )

        analysis_result = {
            "backend": {},
            "frontend": {},
            "database": {},
            "apis": [],
            "requirements": {},
        }

        warnings = []
        errors = []

        try:
            # Analyze backend
            backend_path = source_path / self.config["source"]["backend"]["path"]
            if backend_path.exists():
                self.logger.info("Analyzing Spring Boot backend")
                backend_analysis = await self._analyze_spring_boot(backend_path)
                analysis_result["backend"] = backend_analysis
            else:
                errors.append(f"Backend path not found: {backend_path}")

            # Analyze frontend
            frontend_path = source_path / self.config["source"]["frontend"]["path"]
            if frontend_path.exists():
                self.logger.info("Analyzing React frontend")
                frontend_analysis = await self._analyze_react(frontend_path)
                analysis_result["frontend"] = frontend_analysis
            else:
                errors.append(f"Frontend path not found: {frontend_path}")

            # Extract database configuration
            if "database_config" in analysis_result["backend"]:
                db_config = analysis_result["backend"]["database_config"]
                analysis_result["database"] = await self._analyze_database(db_config)

            # Use Claude to generate migration recommendations
            if not errors:
                recommendations = await self._generate_recommendations(analysis_result)
                analysis_result["requirements"]["recommendations"] = recommendations
            else:
                warnings.append("Skipping AI recommendations due to analysis errors")

            # Publish analysis complete event
            await self.event_bus.publish(Event(
                event_type=EventType.ANALYSIS_COMPLETE,
                source_agent=self.name,
                data=analysis_result,
            ))

            status = AgentStatus.SUCCESS if not errors else AgentStatus.FAILED

            return AgentResult(
                status=status,
                data=analysis_result,
                errors=errors,
                warnings=warnings,
                metadata={
                    "source_path": str(source_path),
                    "backend_analyzed": "backend" in analysis_result,
                    "frontend_analyzed": "frontend" in analysis_result,
                }
            )

        except Exception as e:
            self.logger.error(f"Analysis error: {str(e)}", exc_info=True)
            return AgentResult(
                status=AgentStatus.FAILED,
                data=analysis_result,
                errors=[str(e)],
            )

    async def _analyze_spring_boot(self, backend_path: Path) -> Dict[str, Any]:
        """
        Analyze Spring Boot application.

        Args:
            backend_path: Path to backend directory

        Returns:
            Dictionary with backend analysis
        """
        analysis = {
            "build_tool": None,
            "java_version": None,
            "spring_boot_version": None,
            "dependencies": [],
            "database_config": {},
            "server_config": {},
            "controllers": [],
        }

        # Detect build tool
        if (backend_path / "pom.xml").exists():
            analysis["build_tool"] = "maven"
            await self._analyze_maven(backend_path, analysis)
        elif (backend_path / "build.gradle").exists():
            analysis["build_tool"] = "gradle"
            await self._analyze_gradle(backend_path, analysis)

        # Analyze application.properties or application.yml
        props_file = backend_path / "src" / "main" / "resources" / "application.properties"
        yml_file = backend_path / "src" / "main" / "resources" / "application.yml"

        if props_file.exists():
            await self._analyze_application_properties(props_file, analysis)
        elif yml_file.exists():
            await self._analyze_application_yml(yml_file, analysis)

        # Find controllers
        src_main_java = backend_path / "src" / "main" / "java"
        if src_main_java.exists():
            analysis["controllers"] = await self._find_controllers(src_main_java)

        return analysis

    async def _analyze_maven(self, backend_path: Path, analysis: Dict[str, Any]) -> None:
        """Analyze Maven pom.xml."""
        pom_file = backend_path / "pom.xml"

        try:
            tree = ET.parse(pom_file)
            root = tree.getroot()

            # Define namespace
            ns = {"m": "http://maven.apache.org/POM/4.0.0"}

            # Get Java version
            java_version = root.find(".//m:properties/m:java.version", ns)
            if java_version is not None:
                analysis["java_version"] = java_version.text

            # Get Spring Boot version from parent
            parent = root.find("m:parent", ns)
            if parent is not None:
                version = parent.find("m:version", ns)
                if version is not None:
                    analysis["spring_boot_version"] = version.text

            # Get dependencies
            dependencies = root.findall(".//m:dependency", ns)
            for dep in dependencies:
                artifact = dep.find("m:artifactId", ns)
                if artifact is not None:
                    analysis["dependencies"].append(artifact.text)

        except Exception as e:
            self.logger.warning(f"Error parsing pom.xml: {str(e)}")

    async def _analyze_gradle(self, backend_path: Path, analysis: Dict[str, Any]) -> None:
        """Analyze Gradle build.gradle."""
        gradle_file = backend_path / "build.gradle"

        try:
            content = gradle_file.read_text()

            # Extract Java version
            java_version_match = re.search(r"sourceCompatibility\s*=\s*['\"]?([\d.]+)", content)
            if java_version_match:
                analysis["java_version"] = java_version_match.group(1)

            # Extract dependencies
            deps = re.findall(r"implementation\s+['\"]([^'\"]+)['\"]", content)
            analysis["dependencies"] = deps

        except Exception as e:
            self.logger.warning(f"Error parsing build.gradle: {str(e)}")

    async def _analyze_application_properties(
        self, props_file: Path, analysis: Dict[str, Any]
    ) -> None:
        """Analyze application.properties file."""
        try:
            content = props_file.read_text()
            lines = content.split("\n")

            db_config = {}
            server_config = {}

            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Database configuration
                    if key.startswith("spring.datasource"):
                        db_key = key.replace("spring.datasource.", "")
                        db_config[db_key] = value
                    elif key.startswith("spring.h2"):
                        db_key = key.replace("spring.h2.", "")
                        db_config[db_key] = value
                    elif key.startswith("spring.jpa"):
                        db_key = key.replace("spring.jpa.", "")
                        db_config[db_key] = value

                    # Server configuration
                    elif key.startswith("server."):
                        server_key = key.replace("server.", "")
                        server_config[server_key] = value

            analysis["database_config"] = db_config
            analysis["server_config"] = server_config

        except Exception as e:
            self.logger.warning(f"Error parsing application.properties: {str(e)}")

    async def _analyze_application_yml(
        self, yml_file: Path, analysis: Dict[str, Any]
    ) -> None:
        """Analyze application.yml file."""
        try:
            import yaml

            content = yml_file.read_text()
            data = yaml.safe_load(content)

            if "spring" in data:
                if "datasource" in data["spring"]:
                    analysis["database_config"] = data["spring"]["datasource"]
                if "h2" in data["spring"]:
                    analysis["database_config"]["h2"] = data["spring"]["h2"]
                if "jpa" in data["spring"]:
                    analysis["database_config"]["jpa"] = data["spring"]["jpa"]

            if "server" in data:
                analysis["server_config"] = data["server"]

        except Exception as e:
            self.logger.warning(f"Error parsing application.yml: {str(e)}")

    async def _find_controllers(self, src_path: Path) -> List[Dict[str, Any]]:
        """Find REST controllers and extract endpoints."""
        controllers = []

        try:
            for java_file in src_path.rglob("*.java"):
                content = java_file.read_text()

                # Check if it's a controller
                if "@RestController" in content or "@Controller" in content:
                    controller_info = {
                        "file": str(java_file),
                        "endpoints": [],
                    }

                    # Extract base mapping
                    base_mapping = ""
                    base_match = re.search(r"@RequestMapping\([\"']([^\"']+)[\"']\)", content)
                    if base_match:
                        base_mapping = base_match.group(1)

                    # Extract endpoints
                    endpoint_patterns = [
                        r"@GetMapping\([\"']([^\"']+)[\"']\)",
                        r"@PostMapping\([\"']([^\"']+)[\"']\)",
                        r"@PutMapping\([\"']([^\"']+)[\"']\)",
                        r"@DeleteMapping\([\"']([^\"']+)[\"']\)",
                        r"@PatchMapping\([\"']([^\"']+)[\"']\)",
                    ]

                    for pattern in endpoint_patterns:
                        matches = re.findall(pattern, content)
                        for match in matches:
                            endpoint = base_mapping + match
                            method = pattern.split("@")[1].split("Mapping")[0].upper()
                            controller_info["endpoints"].append({
                                "method": method,
                                "path": endpoint,
                            })

                    if controller_info["endpoints"]:
                        controllers.append(controller_info)

        except Exception as e:
            self.logger.warning(f"Error finding controllers: {str(e)}")

        return controllers

    async def _analyze_react(self, frontend_path: Path) -> Dict[str, Any]:
        """
        Analyze React application.

        Args:
            frontend_path: Path to frontend directory

        Returns:
            Dictionary with frontend analysis
        """
        analysis = {
            "build_tool": None,
            "node_version": None,
            "react_version": None,
            "dependencies": [],
            "api_endpoints": [],
            "env_vars": [],
        }

        # Analyze package.json
        package_json = frontend_path / "package.json"
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text())

                # Extract React version
                if "dependencies" in data and "react" in data["dependencies"]:
                    analysis["react_version"] = data["dependencies"]["react"]

                # Extract all dependencies
                if "dependencies" in data:
                    analysis["dependencies"] = list(data["dependencies"].keys())

                # Detect build tool from scripts
                if "scripts" in data:
                    if "vite" in str(data["scripts"]):
                        analysis["build_tool"] = "vite"
                    elif "react-scripts" in str(data["scripts"]):
                        analysis["build_tool"] = "create-react-app"
                    elif "webpack" in str(data["scripts"]):
                        analysis["build_tool"] = "webpack"

            except Exception as e:
                self.logger.warning(f"Error parsing package.json: {str(e)}")

        # Find API endpoint configurations
        src_path = frontend_path / "src"
        if src_path.exists():
            analysis["api_endpoints"] = await self._find_api_endpoints(src_path)

        # Check for environment variables
        env_files = [".env", ".env.local", ".env.production"]
        for env_file in env_files:
            env_path = frontend_path / env_file
            if env_path.exists():
                try:
                    content = env_path.read_text()
                    vars = re.findall(r"^([A-Z_]+)=", content, re.MULTILINE)
                    analysis["env_vars"].extend(vars)
                except Exception as e:
                    self.logger.warning(f"Error reading {env_file}: {str(e)}")

        return analysis

    async def _find_api_endpoints(self, src_path: Path) -> List[str]:
        """Find API endpoint configurations in React code."""
        endpoints = []

        try:
            for file in src_path.rglob("*.js"):
                content = file.read_text()

                # Find API base URLs
                api_urls = re.findall(
                    r"['\"]https?://[^'\"]+['\"]|['\"]http://localhost:\d+['\"]",
                    content
                )
                endpoints.extend([url.strip("'\"") for url in api_urls])

            for file in src_path.rglob("*.jsx"):
                content = file.read_text()
                api_urls = re.findall(
                    r"['\"]https?://[^'\"]+['\"]|['\"]http://localhost:\d+['\"]",
                    content
                )
                endpoints.extend([url.strip("'\"") for url in api_urls])

            for file in src_path.rglob("*.ts"):
                content = file.read_text()
                api_urls = re.findall(
                    r"['\"]https?://[^'\"]+['\"]|['\"]http://localhost:\d+['\"]",
                    content
                )
                endpoints.extend([url.strip("'\"") for url in api_urls])

            for file in src_path.rglob("*.tsx"):
                content = file.read_text()
                api_urls = re.findall(
                    r"['\"]https?://[^'\"]+['\"]|['\"]http://localhost:\d+['\"]",
                    content
                )
                endpoints.extend([url.strip("'\"") for url in api_urls])

        except Exception as e:
            self.logger.warning(f"Error finding API endpoints: {str(e)}")

        return list(set(endpoints))  # Remove duplicates

    async def _analyze_database(self, db_config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze database configuration."""
        database_info = {
            "type": "unknown",
            "mode": "unknown",
            "migration_recommended": False,
            "migration_notes": [],
        }

        # Detect database type
        url = db_config.get("url", "")

        if "h2:mem:" in url:
            database_info["type"] = "h2"
            database_info["mode"] = "in-memory"
            database_info["migration_recommended"] = True
            database_info["migration_notes"].append(
                "H2 in-memory database detected. Data will be lost on restart."
            )
            database_info["migration_notes"].append(
                "Recommend migrating to Cloud SQL for persistence."
            )
        elif "h2:file:" in url or "h2:" in url:
            database_info["type"] = "h2"
            database_info["mode"] = "file-based"
            database_info["migration_recommended"] = True
            database_info["migration_notes"].append(
                "H2 file-based database detected. Consider Cloud SQL for scalability."
            )
        elif "mysql" in url:
            database_info["type"] = "mysql"
            database_info["migration_recommended"] = True
            database_info["migration_notes"].append(
                "MySQL detected. Can migrate to Cloud SQL MySQL."
            )
        elif "postgresql" in url:
            database_info["type"] = "postgresql"
            database_info["migration_recommended"] = True
            database_info["migration_notes"].append(
                "PostgreSQL detected. Can migrate to Cloud SQL PostgreSQL."
            )

        return database_info

    async def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Use Claude to generate migration recommendations."""
        try:
            prompt = f"""
Analyze the following application structure and provide migration recommendations for GCP:

Backend Analysis:
{json.dumps(analysis.get('backend', {}), indent=2)}

Frontend Analysis:
{json.dumps(analysis.get('frontend', {}), indent=2)}

Database Analysis:
{json.dumps(analysis.get('database', {}), indent=2)}

Provide 3-5 specific, actionable recommendations for migrating this application to Google Cloud Platform.
Focus on:
1. Database migration strategy
2. Container optimization for Cloud Run
3. Frontend hosting best practices
4. Configuration management
5. Security considerations

Format your response as a JSON array of strings.
"""

            response = await self.ask_claude(
                prompt=prompt,
                system_prompt="You are a cloud migration expert specializing in GCP.",
                max_tokens=2000,
            )

            # Try to parse as JSON
            try:
                recommendations = json.loads(response)
                if isinstance(recommendations, list):
                    return recommendations
            except json.JSONDecodeError:
                # If not valid JSON, split by newlines and filter
                lines = response.strip().split("\n")
                recommendations = [line.strip() for line in lines if line.strip() and not line.strip().startswith("[") and not line.strip().startswith("]")]
                return recommendations[:5]

            return []

        except Exception as e:
            self.logger.warning(f"Could not generate AI recommendations: {str(e)}")
            return [
                "Review database persistence strategy for H2",
                "Configure environment variables for Cloud Run",
                "Set up CORS for frontend-backend communication",
                "Implement health check endpoints",
                "Review and update API endpoint URLs",
            ]
