"""
Code Analyzer Agent — Powered by Dedalus SDK

Analyzes the source application using:
- REASONING model (GPT-4.1) for deep code analysis
- Local tools for scanning pom.xml, gradle, properties, and React apps
- MCP server (Brave Search) for researching migration best practices
"""

import json
from pathlib import Path
from typing import Any, Dict

from .base_agent import AgentResult, AgentStatus, BaseAgent, Event, EventType, ModelRole
from .dedalus_tools import (
    ANALYSIS_TOOLS,
    analyze_react_app,
    analyze_spring_properties,
    detect_database_type,
    extract_api_endpoints,
    scan_gradle_build,
    scan_maven_pom,
)


class CodeAnalyzerAgent(BaseAgent):
    """
    Code Analyzer agent powered by Dedalus SDK.

    Uses the REASONING model for deep analysis and local tools for
    scanning source code artifacts.
    """

    def __init__(self, event_bus, config: Dict[str, Any], dedalus_api_key: str):
        super().__init__(
            name="CodeAnalyzer",
            event_bus=event_bus,
            config=config,
            dedalus_api_key=dedalus_api_key,
        )

    async def _execute_impl(self) -> AgentResult:
        """Execute code analysis using Dedalus tools and multi-model routing."""
        self.logger.info("Starting code analysis with Dedalus REASONING model")

        source_path = Path(self.config["source"]["path"])
        if not source_path.exists():
            return AgentResult(
                status=AgentStatus.FAILED,
                data={},
                errors=[f"Source path does not exist: {source_path}"],
            )

        analysis_result: Dict[str, Any] = {
            "backend": {},
            "frontend": {},
            "database": {},
            "apis": [],
            "requirements": {},
        }
        warnings: list[str] = []
        errors: list[str] = []

        try:
            backend_path = source_path / self.config["source"]["backend"]["path"]
            frontend_path = source_path / self.config["source"]["frontend"]["path"]

            # Phase 1: Use tools directly to gather raw data
            if backend_path.exists():
                self.logger.info("Scanning backend with Dedalus tools")
                backend_analysis = await self._analyze_backend(str(backend_path))
                analysis_result["backend"] = backend_analysis
            else:
                errors.append(f"Backend path not found: {backend_path}")

            if frontend_path.exists():
                self.logger.info("Scanning frontend with Dedalus tools")
                frontend_raw = await self._invoke_tool(analyze_react_app, str(frontend_path))
                analysis_result["frontend"] = json.loads(frontend_raw)
            else:
                errors.append(f"Frontend path not found: {frontend_path}")

            # Phase 2: Analyze database config
            db_url = analysis_result["backend"].get("database_config", {}).get(
                "spring.datasource.url", ""
            )
            if db_url:
                db_raw = await self._invoke_tool(detect_database_type, db_url)
                analysis_result["database"] = json.loads(db_raw)

            # Phase 3: Use Dedalus REASONING model + tools + MCP for recommendations
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
                    "backend_analyzed": bool(analysis_result["backend"]),
                    "frontend_analyzed": bool(analysis_result["frontend"]),
                },
            )

        except Exception as e:
            self.logger.error(f"Analysis error: {str(e)}", exc_info=True)
            return AgentResult(
                status=AgentStatus.FAILED,
                data=analysis_result,
                errors=[str(e)],
            )

    async def _analyze_backend(self, backend_path: str) -> Dict[str, Any]:
        """Analyze Spring Boot backend using Dedalus tools."""
        analysis: Dict[str, Any] = {
            "build_tool": None,
            "java_version": None,
            "spring_boot_version": None,
            "dependencies": [],
            "database_config": {},
            "server_config": {},
            "controllers": [],
        }

        bp = Path(backend_path)

        # Detect build tool and parse
        if (bp / "pom.xml").exists():
            analysis["build_tool"] = "maven"
            maven_raw = await self._invoke_tool(scan_maven_pom, backend_path)
            maven_data = json.loads(maven_raw)
            analysis["java_version"] = maven_data.get("java_version")
            analysis["spring_boot_version"] = maven_data.get("spring_boot_version")
            analysis["dependencies"] = maven_data.get("dependencies", [])
        elif (bp / "build.gradle").exists():
            analysis["build_tool"] = "gradle"
            gradle_raw = await self._invoke_tool(scan_gradle_build, backend_path)
            gradle_data = json.loads(gradle_raw)
            analysis["java_version"] = gradle_data.get("java_version")
            analysis["dependencies"] = gradle_data.get("dependencies", [])

        # Analyze properties
        props_raw = await self._invoke_tool(analyze_spring_properties, backend_path)
        props_data = json.loads(props_raw)
        analysis["database_config"] = props_data.get("database_config", {})
        analysis["server_config"] = props_data.get("server_config", {})

        # Extract API endpoints
        endpoints_raw = await self._invoke_tool(extract_api_endpoints, backend_path)
        analysis["controllers"] = json.loads(endpoints_raw)

        return analysis

    async def _generate_recommendations(self, analysis: Dict[str, Any]) -> list[str]:
        """Use Dedalus REASONING model + Brave Search MCP for migration recommendations.

        This is a key handoff: the REASONING model analyzes the code structure
        while Brave Search MCP provides real-time best practices.
        """
        try:
            prompt = f"""Analyze this application structure and provide migration recommendations for GCP:

Backend Analysis:
{json.dumps(analysis.get('backend', {}), indent=2)}

Frontend Analysis:
{json.dumps(analysis.get('frontend', {}), indent=2)}

Database Analysis:
{json.dumps(analysis.get('database', {}), indent=2)}

Provide 3-5 specific, actionable recommendations for migrating this application to Google Cloud Platform.
Focus on: database migration strategy, container optimization for Cloud Run, frontend hosting best practices, configuration management, and security.

Format your response as a JSON array of strings."""

            response = await self.run_with_dedalus(
                prompt=prompt,
                # REASONING model for deep analysis + route to research model
                model=[ModelRole.REASONING.value, ModelRole.PLANNING.value],
                tools=ANALYSIS_TOOLS,
                mcp_servers=["windsor/brave-search-mcp"],
                instructions="You are a cloud migration expert specializing in GCP. Use Brave Search to look up current best practices if needed.",
                max_steps=5,
            )

            # Parse response
            try:
                recommendations = json.loads(response)
                if isinstance(recommendations, list):
                    return recommendations
            except json.JSONDecodeError:
                lines = response.strip().split("\n")
                return [
                    line.strip()
                    for line in lines
                    if line.strip() and not line.strip().startswith("[") and not line.strip().startswith("]")
                ][:5]

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
