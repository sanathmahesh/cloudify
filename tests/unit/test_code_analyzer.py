"""
Unit tests for Code Analyzer Agent.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from agents.base_agent import AgentStatus, EventBus
from agents.code_analyzer import CodeAnalyzerAgent


@pytest.fixture
def event_bus():
    """Create event bus fixture."""
    return EventBus()


@pytest.fixture
def config():
    """Create configuration fixture."""
    return {
        "source": {
            "path": "/tmp/test-app",
            "backend": {
                "type": "spring-boot",
                "path": "backend",
            },
            "frontend": {
                "type": "react",
                "path": "frontend",
            },
        },
        "ai": {
            "model": "claude-opus-4.6",
            "temperature": 0.3,
        },
    }


@pytest.fixture
def code_analyzer(event_bus, config):
    """Create CodeAnalyzerAgent fixture."""
    return CodeAnalyzerAgent(
        event_bus=event_bus,
        config=config,
        claude_api_key="test-api-key",
    )


@pytest.mark.asyncio
async def test_analyzer_initialization(code_analyzer):
    """Test agent initialization."""
    assert code_analyzer.name == "CodeAnalyzer"
    assert code_analyzer.status.value == "idle"


@pytest.mark.asyncio
async def test_analyzer_invalid_source_path(code_analyzer):
    """Test analyzer with invalid source path."""
    result = await code_analyzer.execute()

    assert result.status == AgentStatus.FAILED
    assert len(result.errors) > 0
    assert "does not exist" in result.errors[0]


@pytest.mark.asyncio
async def test_analyze_maven_pom(code_analyzer, tmp_path):
    """Test Maven pom.xml analysis."""
    # Create test pom.xml
    backend_path = tmp_path / "backend"
    backend_path.mkdir()

    pom_xml = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <properties>
        <java.version>21</java.version>
    </properties>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.5.0</version>
    </parent>
    <dependencies>
        <dependency>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
    </dependencies>
</project>
"""
    (backend_path / "pom.xml").write_text(pom_xml)

    # Analyze
    analysis = {}
    await code_analyzer._analyze_maven(backend_path, analysis)

    assert analysis["java_version"] == "21"
    assert analysis["spring_boot_version"] == "3.5.0"
    assert "spring-boot-starter-web" in analysis["dependencies"]


@pytest.mark.asyncio
async def test_analyze_application_properties(code_analyzer, tmp_path):
    """Test application.properties analysis."""
    backend_path = tmp_path / "backend"
    src_path = backend_path / "src" / "main" / "resources"
    src_path.mkdir(parents=True)

    props = """spring.application.name=test-app
server.port=8080
spring.datasource.url=jdbc:h2:mem:testdb
spring.datasource.username=sa
spring.datasource.password=
"""
    (src_path / "application.properties").write_text(props)

    analysis = {}
    await code_analyzer._analyze_application_properties(
        src_path / "application.properties", analysis
    )

    assert "url" in analysis["database_config"]
    assert "jdbc:h2:mem:testdb" in analysis["database_config"]["url"]
    assert "port" in analysis["server_config"]
    assert analysis["server_config"]["port"] == "8080"


@pytest.mark.asyncio
async def test_analyze_database_h2_memory(code_analyzer):
    """Test H2 in-memory database analysis."""
    db_config = {
        "url": "jdbc:h2:mem:testdb",
        "username": "sa",
    }

    result = await code_analyzer._analyze_database(db_config)

    assert result["type"] == "h2"
    assert result["mode"] == "in-memory"
    assert result["migration_recommended"] is True
    assert len(result["migration_notes"]) > 0


@pytest.mark.asyncio
async def test_find_api_endpoints(code_analyzer, tmp_path):
    """Test API endpoint detection in React code."""
    frontend_path = tmp_path / "frontend"
    src_path = frontend_path / "src"
    src_path.mkdir(parents=True)

    # Create test React file
    react_code = """
import axios from 'axios';

const API_URL = 'http://localhost:8080';

export const fetchData = () => {
    return axios.get(`${API_URL}/api/data`);
};
"""
    (src_path / "api.js").write_text(react_code)

    endpoints = await code_analyzer._find_api_endpoints(src_path)

    assert len(endpoints) > 0
    assert "http://localhost:8080" in endpoints
