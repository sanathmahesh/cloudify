"""
Dedalus SDK Tool Definitions for Cloudify.

All GCP operations, code analysis, and deployment functions are defined here
as properly typed tools with docstrings so the Dedalus SDK can auto-extract
schemas and let models invoke them during agentic loops.
"""

import asyncio
import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Shell helpers (not exposed as tools – used internally by tools)
# ---------------------------------------------------------------------------

async def _run_command(command: str, cwd: str | None = None) -> dict[str, Any]:
    """Run a shell command asynchronously and return result dict."""
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await process.communicate()
        return {
            "returncode": process.returncode,
            "stdout": stdout.decode() if stdout else "",
            "stderr": stderr.decode() if stderr else "",
        }
    except Exception as e:
        return {"returncode": 1, "stdout": "", "stderr": str(e)}


async def _run_gcloud(command: str) -> dict[str, Any]:
    """Run a gcloud CLI command."""
    return await _run_command(f"gcloud {command}")


# ============================================================================
# CODE ANALYSIS TOOLS
# ============================================================================

async def scan_maven_pom(backend_path: str) -> str:
    """Parse a Maven pom.xml to extract Java version, Spring Boot version, and dependencies.

    Args:
        backend_path: Absolute path to the backend directory containing pom.xml.

    Returns:
        JSON string with keys: java_version, spring_boot_version, dependencies.
    """
    pom_file = Path(backend_path) / "pom.xml"
    result: dict[str, Any] = {"java_version": None, "spring_boot_version": None, "dependencies": []}

    if not pom_file.exists():
        return json.dumps({"error": f"pom.xml not found at {pom_file}"})

    try:
        tree = ET.parse(pom_file)
        root = tree.getroot()
        ns = {"m": "http://maven.apache.org/POM/4.0.0"}

        java_version = root.find(".//m:properties/m:java.version", ns)
        if java_version is not None:
            result["java_version"] = java_version.text

        parent = root.find("m:parent", ns)
        if parent is not None:
            version = parent.find("m:version", ns)
            if version is not None:
                result["spring_boot_version"] = version.text

        for dep in root.findall(".//m:dependency", ns):
            artifact = dep.find("m:artifactId", ns)
            if artifact is not None:
                result["dependencies"].append(artifact.text)
    except Exception as e:
        result["error"] = str(e)

    return json.dumps(result)


async def scan_gradle_build(backend_path: str) -> str:
    """Parse a Gradle build.gradle to extract Java version and dependencies.

    Args:
        backend_path: Absolute path to the backend directory containing build.gradle.

    Returns:
        JSON string with keys: java_version, dependencies.
    """
    gradle_file = Path(backend_path) / "build.gradle"
    result: dict[str, Any] = {"java_version": None, "dependencies": []}

    if not gradle_file.exists():
        return json.dumps({"error": f"build.gradle not found at {gradle_file}"})

    try:
        content = gradle_file.read_text()
        match = re.search(r"sourceCompatibility\s*=\s*['\"]?([\d.]+)", content)
        if match:
            result["java_version"] = match.group(1)
        result["dependencies"] = re.findall(r"implementation\s+['\"]([^'\"]+)['\"]", content)
    except Exception as e:
        result["error"] = str(e)

    return json.dumps(result)


async def analyze_spring_properties(backend_path: str) -> str:
    """Analyze Spring Boot application.properties or application.yml for database and server config.

    Args:
        backend_path: Absolute path to the backend directory.

    Returns:
        JSON string with keys: database_config, server_config.
    """
    base = Path(backend_path) / "src" / "main" / "resources"
    db_config: dict[str, str] = {}
    server_config: dict[str, str] = {}

    props_file = base / "application.properties"
    yml_file = base / "application.yml"

    if props_file.exists():
        content = props_file.read_text()
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip()
            if key.startswith("spring.datasource") or key.startswith("spring.h2") or key.startswith("spring.jpa"):
                db_config[key] = value
            elif key.startswith("server."):
                server_config[key] = value
    elif yml_file.exists():
        import yaml
        data = yaml.safe_load(yml_file.read_text())
        if isinstance(data, dict) and "spring" in data:
            spring = data["spring"]
            if "datasource" in spring:
                db_config.update({f"spring.datasource.{k}": str(v) for k, v in spring["datasource"].items()})
            if "h2" in spring:
                db_config["spring.h2"] = json.dumps(spring["h2"])
            if "jpa" in spring:
                db_config.update({f"spring.jpa.{k}": str(v) for k, v in spring["jpa"].items()})
        if isinstance(data, dict) and "server" in data:
            server_config.update({f"server.{k}": str(v) for k, v in data["server"].items()})

    return json.dumps({"database_config": db_config, "server_config": server_config})


async def detect_database_type(datasource_url: str) -> str:
    """Detect the database type and mode from a JDBC datasource URL.

    Args:
        datasource_url: The spring.datasource.url value (JDBC URL).

    Returns:
        JSON string with keys: type, mode, migration_recommended, notes.
    """
    info: dict[str, Any] = {"type": "unknown", "mode": "unknown", "migration_recommended": False, "notes": []}

    if "h2:mem:" in datasource_url:
        info.update(type="h2", mode="in-memory", migration_recommended=True)
        info["notes"].append("H2 in-memory database – data lost on restart. Recommend Cloud SQL.")
    elif "h2:" in datasource_url:
        info.update(type="h2", mode="file-based", migration_recommended=True)
        info["notes"].append("H2 file-based – not persistent on Cloud Run. Consider Cloud SQL.")
    elif "mysql" in datasource_url:
        info.update(type="mysql", mode="external", migration_recommended=True)
        info["notes"].append("MySQL detected. Can migrate to Cloud SQL MySQL.")
    elif "postgresql" in datasource_url:
        info.update(type="postgresql", mode="external", migration_recommended=True)
        info["notes"].append("PostgreSQL detected. Can migrate to Cloud SQL PostgreSQL.")

    return json.dumps(info)


async def extract_api_endpoints(backend_path: str) -> str:
    """Find REST controllers and their endpoint mappings in a Spring Boot project.

    Args:
        backend_path: Absolute path to the backend directory.

    Returns:
        JSON string – list of {file, endpoints: [{method, path}]}.
    """
    src_java = Path(backend_path) / "src" / "main" / "java"
    controllers: list[dict[str, Any]] = []

    if not src_java.exists():
        return json.dumps([])

    for java_file in src_java.rglob("*.java"):
        content = java_file.read_text()
        if "@RestController" not in content and "@Controller" not in content:
            continue

        endpoints: list[dict[str, str]] = []
        base = ""
        base_match = re.search(r"@RequestMapping\([\"']([^\"']+)[\"']\)", content)
        if base_match:
            base = base_match.group(1)

        for pattern in [
            r"@GetMapping\([\"']([^\"']+)[\"']\)",
            r"@PostMapping\([\"']([^\"']+)[\"']\)",
            r"@PutMapping\([\"']([^\"']+)[\"']\)",
            r"@DeleteMapping\([\"']([^\"']+)[\"']\)",
            r"@PatchMapping\([\"']([^\"']+)[\"']\)",
        ]:
            method = pattern.split("@")[1].split("Mapping")[0].upper()
            for m in re.findall(pattern, content):
                endpoints.append({"method": method, "path": base + m})

        if endpoints:
            controllers.append({"file": str(java_file), "endpoints": endpoints})

    return json.dumps(controllers)


async def analyze_react_app(frontend_path: str) -> str:
    """Analyze a React frontend – package.json, build tool, dependencies, and API endpoints.

    Args:
        frontend_path: Absolute path to the frontend directory.

    Returns:
        JSON string with keys: build_tool, react_version, dependencies, api_endpoints.
    """
    fp = Path(frontend_path)
    analysis: dict[str, Any] = {"build_tool": None, "react_version": None, "dependencies": [], "api_endpoints": []}

    pkg = fp / "package.json"
    if pkg.exists():
        data = json.loads(pkg.read_text())
        deps = data.get("dependencies", {})
        analysis["react_version"] = deps.get("react")
        analysis["dependencies"] = list(deps.keys())
        scripts = str(data.get("scripts", {}))
        if "vite" in scripts:
            analysis["build_tool"] = "vite"
        elif "react-scripts" in scripts:
            analysis["build_tool"] = "create-react-app"
        elif "webpack" in scripts:
            analysis["build_tool"] = "webpack"

    # Find hardcoded API URLs
    src = fp / "src"
    if src.exists():
        endpoints: set[str] = set()
        for ext in ("*.js", "*.jsx", "*.ts", "*.tsx"):
            for f in src.rglob(ext):
                content = f.read_text()
                urls = re.findall(r"['\"]https?://[^'\"]+['\"]|['\"]http://localhost:\d+['\"]", content)
                endpoints.update(url.strip("'\"") for url in urls)
        analysis["api_endpoints"] = list(endpoints)

    return json.dumps(analysis)


# ============================================================================
# GCP INFRASTRUCTURE TOOLS
# ============================================================================

async def check_gcloud_auth() -> str:
    """Check if the gcloud CLI is installed and authenticated.

    Returns:
        JSON string with keys: installed, authenticated, active_account.
    """
    version = await _run_command("gcloud --version")
    if version["returncode"] != 0:
        return json.dumps({"installed": False, "authenticated": False, "active_account": None})

    auth = await _run_command("gcloud auth list")
    authenticated = auth["returncode"] == 0 and ("*" in auth["stdout"] or "ACTIVE" in auth["stdout"])
    return json.dumps({"installed": True, "authenticated": authenticated, "active_account": auth["stdout"][:200]})


async def enable_gcp_apis(project_id: str, apis: list[str]) -> str:
    """Enable Google Cloud APIs for a project.

    Args:
        project_id: The GCP project ID.
        apis: List of API identifiers to enable (e.g. ['run.googleapis.com']).

    Returns:
        JSON string with per-API status.
    """
    results: dict[str, str] = {}
    for api in apis:
        r = await _run_gcloud(f"services enable {api} --project={project_id}")
        results[api] = "enabled" if r["returncode"] == 0 else f"failed: {r['stderr'][:200]}"
    return json.dumps(results)


async def create_artifact_registry(project_id: str, region: str, repo_name: str) -> str:
    """Create a Docker Artifact Registry repository if it doesn't exist.

    Args:
        project_id: GCP project ID.
        region: GCP region (e.g. us-central1).
        repo_name: Name for the Artifact Registry repository.

    Returns:
        JSON string with repository_url and status.
    """
    check = await _run_gcloud(f"artifacts repositories describe {repo_name} --location={region}")
    if check["returncode"] != 0:
        create = await _run_gcloud(
            f"artifacts repositories create {repo_name} "
            f"--repository-format=docker --location={region} "
            f"--description='Cloudify migrated images' --project={project_id}"
        )
        if create["returncode"] != 0:
            return json.dumps({"success": False, "error": create["stderr"][:300]})

    url = f"{region}-docker.pkg.dev/{project_id}/{repo_name}"
    return json.dumps({"success": True, "repository_url": url})


async def setup_firebase_project(project_id: str) -> str:
    """Verify Firebase CLI is installed and the project is accessible.

    Args:
        project_id: GCP/Firebase project ID.

    Returns:
        JSON string with status and hosting_site.
    """
    check = await _run_command("firebase --version")
    if check["returncode"] != 0:
        return json.dumps({"success": False, "error": "Firebase CLI not installed. Run: npm install -g firebase-tools"})
    return json.dumps({"success": True, "hosting_site": f"{project_id}.web.app"})


async def configure_iam_permissions(project_id: str) -> str:
    """Configure IAM permissions for Cloud Build to deploy to Cloud Run.

    Args:
        project_id: GCP project ID.

    Returns:
        JSON string with project_number, service_account, roles_granted.
    """
    r = await _run_gcloud(f"projects describe {project_id} --format='value(projectNumber)'")
    if r["returncode"] != 0:
        return json.dumps({"success": False, "error": "Could not get project number"})

    project_number = r["stdout"].strip()
    sa = f"{project_number}@cloudbuild.gserviceaccount.com"
    roles = ["roles/run.admin", "roles/iam.serviceAccountUser"]

    for role in roles:
        await _run_gcloud(
            f"projects add-iam-policy-binding {project_id} "
            f"--member=serviceAccount:{sa} --role={role}"
        )

    return json.dumps({"success": True, "project_number": project_number, "service_account": sa, "roles_granted": roles})


# ============================================================================
# DATABASE TOOLS
# ============================================================================

async def create_cloud_sql_instance(
    project_id: str,
    region: str,
    instance_name: str,
    database_name: str,
    tier: str,
    db_version: str,
) -> str:
    """Create a Cloud SQL instance and database.

    Args:
        project_id: GCP project ID.
        region: GCP region.
        instance_name: Name for the Cloud SQL instance.
        database_name: Name for the database to create inside the instance.
        tier: Machine tier (e.g. db-f1-micro).
        db_version: Database engine version (e.g. POSTGRES_15).

    Returns:
        JSON string with connection_name and status.
    """
    create = await _run_command(
        f"gcloud sql instances create {instance_name} "
        f"--database-version={db_version} --tier={tier} "
        f"--region={region} --project={project_id}"
    )
    if create["returncode"] != 0 and "already exists" not in create["stderr"]:
        return json.dumps({"success": False, "error": create["stderr"][:300]})

    await _run_command(
        f"gcloud sql databases create {database_name} "
        f"--instance={instance_name} --project={project_id}"
    )

    conn = await _run_command(
        f"gcloud sql instances describe {instance_name} "
        f"--project={project_id} --format='value(connectionName)'"
    )
    connection_name = conn["stdout"].strip() if conn["returncode"] == 0 else ""

    return json.dumps({
        "success": True,
        "instance_name": instance_name,
        "database_name": database_name,
        "connection_name": connection_name,
    })


# ============================================================================
# DOCKER & DEPLOYMENT TOOLS
# ============================================================================

async def write_dockerfile(backend_path: str, content: str) -> str:
    """Write a Dockerfile to the backend directory.

    Args:
        backend_path: Absolute path to the backend directory.
        content: The Dockerfile content to write.

    Returns:
        JSON string with success status and file path.
    """
    try:
        path = Path(backend_path) / "Dockerfile"
        # Clean markdown code fences if present
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```\w*\n?", "", cleaned)
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        path.write_text(cleaned.strip())
        return json.dumps({"success": True, "path": str(path)})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


async def build_docker_image(backend_path: str, image_tag: str) -> str:
    """Build a Docker image for linux/amd64 (required by Cloud Run).

    Args:
        backend_path: Absolute path to the backend directory with Dockerfile.
        image_tag: Full image tag (e.g. us-central1-docker.pkg.dev/proj/repo/svc:latest).

    Returns:
        JSON string with success status.
    """
    r = await _run_command(f"docker build --platform linux/amd64 -t {image_tag} {backend_path}")
    if r["returncode"] == 0:
        return json.dumps({"success": True})
    return json.dumps({"success": False, "error": r["stderr"][:500]})


async def push_docker_image(image_tag: str) -> str:
    """Authenticate with Artifact Registry and push a Docker image.

    Args:
        image_tag: Full image tag to push.

    Returns:
        JSON string with success status.
    """
    region = image_tag.split("-docker")[0]
    await _run_command(f"gcloud auth configure-docker {region}-docker.pkg.dev --quiet")
    r = await _run_command(f"docker push {image_tag}")
    if r["returncode"] == 0:
        return json.dumps({"success": True})
    return json.dumps({"success": False, "error": r["stderr"][:500]})


async def deploy_to_cloud_run(
    project_id: str,
    region: str,
    service_name: str,
    image_tag: str,
    port: int,
    memory: str,
    cpu: str,
    min_instances: int,
    max_instances: int,
    env_vars: dict[str, str],
    allow_unauthenticated: bool,
) -> str:
    """Deploy a Docker image to Google Cloud Run.

    Args:
        project_id: GCP project ID.
        region: GCP region.
        service_name: Cloud Run service name.
        image_tag: Full Docker image tag.
        port: Container port to expose.
        memory: Memory allocation (e.g. 1Gi).
        cpu: CPU allocation (e.g. 1).
        min_instances: Minimum number of instances.
        max_instances: Maximum number of instances.
        env_vars: Environment variables as key-value pairs.
        allow_unauthenticated: Whether to allow unauthenticated access.

    Returns:
        JSON string with success status and service_url.
    """
    cmd_parts = [
        f"gcloud run deploy {service_name}",
        f"--image={image_tag}",
        f"--region={region}",
        f"--project={project_id}",
        f"--platform=managed",
        f"--port={port}",
        f"--memory={memory}",
        f"--cpu={cpu}",
        f"--min-instances={min_instances}",
        f"--max-instances={max_instances}",
    ]
    if env_vars:
        env_str = ",".join(f"{k}={v}" for k, v in env_vars.items())
        cmd_parts.append(f"--set-env-vars={env_str}")
    if allow_unauthenticated:
        cmd_parts.append("--allow-unauthenticated")

    r = await _run_command(" ".join(cmd_parts))
    if r["returncode"] != 0:
        return json.dumps({"success": False, "error": r["stderr"][:500]})

    # Get service URL
    url_result = await _run_gcloud(
        f"run services describe {service_name} --region={region} "
        f"--project={project_id} --format='value(status.url)'"
    )
    service_url = url_result["stdout"].strip() if url_result["returncode"] == 0 else f"https://{service_name}-<hash>.run.app"

    return json.dumps({"success": True, "service_url": service_url})


async def update_cors_origins(backend_path: str, frontend_url: str) -> str:
    """Update CORS configuration in Java source files to include the frontend URL.

    Args:
        backend_path: Absolute path to the backend directory.
        frontend_url: The frontend URL to add to allowed origins.

    Returns:
        JSON string with files_updated count.
    """
    src_java = Path(backend_path) / "src" / "main" / "java"
    if not src_java.exists():
        return json.dumps({"success": False, "error": "No Java source directory found"})

    files_updated = 0
    for java_file in src_java.rglob("*.java"):
        content = java_file.read_text()
        if ".allowedOrigins(" not in content and "@CrossOrigin" not in content:
            continue
        if frontend_url in content:
            files_updated += 1
            continue

        updated = content
        # .allowedOrigins(...) pattern
        pattern = r'(\.allowedOrigins\()([^)]+)(\))'
        match = re.search(pattern, updated)
        if match:
            origins = match.group(2).rstrip()
            updated = updated[:match.start(2)] + f'{origins}, "{frontend_url}"' + updated[match.end(2):]

        # @CrossOrigin(origins = {...}) pattern
        pattern = r'(@CrossOrigin\(origins\s*=\s*\{)([^}]+)(\})'
        match = re.search(pattern, updated)
        if match:
            origins = match.group(2).rstrip()
            updated = updated[:match.start(2)] + f'{origins}, "{frontend_url}"' + updated[match.end(2):]

        # @CrossOrigin(origins = "single") pattern
        pattern = r'(@CrossOrigin\(origins\s*=\s*)"([^"]+)"'
        match = re.search(pattern, updated)
        if match and "{" not in match.group(0):
            orig = match.group(2)
            replacement = f'{match.group(1)}{{"{orig}", "{frontend_url}"}}'
            updated = updated[:match.start()] + replacement + updated[match.end():]

        if updated != content:
            java_file.write_text(updated)
            files_updated += 1

    return json.dumps({"success": True, "files_updated": files_updated})


# ============================================================================
# FRONTEND DEPLOYMENT TOOLS
# ============================================================================

async def configure_frontend_env(frontend_path: str, backend_url: str) -> str:
    """Create .env.production with the backend API URL for a React/Vite app.

    Args:
        frontend_path: Absolute path to the frontend directory.
        backend_url: The deployed backend Cloud Run URL.

    Returns:
        JSON string with success status.
    """
    env_file = Path(frontend_path) / ".env.production"
    env_file.write_text(
        f"# Auto-generated by Cloudify Migration\n"
        f"VITE_API_URL={backend_url}\n"
        f"VITE_BACKEND_URL={backend_url}\n"
    )
    return json.dumps({"success": True, "env_file": str(env_file)})


async def install_npm_dependencies(frontend_path: str) -> str:
    """Install npm dependencies using npm ci (or npm install as fallback).

    Args:
        frontend_path: Absolute path to the frontend directory.

    Returns:
        JSON string with success status.
    """
    fp = Path(frontend_path)
    cmd = "npm ci" if (fp / "package-lock.json").exists() else "npm install"
    r = await _run_command(cmd, cwd=str(fp))
    if r["returncode"] == 0:
        return json.dumps({"success": True})
    return json.dumps({"success": False, "error": r["stderr"][:500]})


async def build_frontend(frontend_path: str) -> str:
    """Build the React production bundle using npm run build.

    Args:
        frontend_path: Absolute path to the frontend directory.

    Returns:
        JSON string with success status and build_dir.
    """
    fp = Path(frontend_path)
    r = await _run_command("npm run build", cwd=str(fp))
    if r["returncode"] != 0:
        return json.dumps({"success": False, "error": r["stderr"][:500]})

    build_dir = fp / "dist" if (fp / "dist").exists() else fp / "build"
    if not build_dir.exists():
        return json.dumps({"success": False, "error": "Build directory not found (expected dist/ or build/)"})

    return json.dumps({"success": True, "build_dir": str(build_dir)})


async def deploy_to_firebase(frontend_path: str, project_id: str, site_name: str) -> str:
    """Initialize Firebase config and deploy to Firebase Hosting.

    Args:
        frontend_path: Absolute path to the frontend directory.
        project_id: GCP/Firebase project ID.
        site_name: Firebase Hosting site name.

    Returns:
        JSON string with success status and hosting_url.
    """
    fp = Path(frontend_path)

    # Determine public directory
    public_dir = "dist" if (fp / "dist").exists() else "build"

    # Write firebase.json
    firebase_config = {
        "hosting": {
            "site": site_name,
            "public": public_dir,
            "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
            "rewrites": [{"source": "**", "destination": "/index.html"}],
        }
    }
    (fp / "firebase.json").write_text(json.dumps(firebase_config, indent=2))

    # Write .firebaserc
    (fp / ".firebaserc").write_text(json.dumps({"projects": {"default": project_id}}, indent=2))

    # Ensure hosting site exists
    await _run_command(f"firebase hosting:sites:create {site_name} --project={project_id}", cwd=str(fp))

    # Deploy
    r = await _run_command(f"firebase deploy --only hosting:{site_name} --project={project_id}", cwd=str(fp))
    if r["returncode"] != 0:
        error = r["stderr"] or r["stdout"]
        return json.dumps({"success": False, "error": error[:500]})

    hosting_url = f"https://{site_name}.web.app"
    # Try to extract actual URL from output
    for line in r["stdout"].split("\n"):
        if "Hosting URL:" in line:
            hosting_url = line.split("Hosting URL:")[-1].strip()
            break

    return json.dumps({"success": True, "hosting_url": hosting_url})


# ============================================================================
# TOOL REGISTRY — Grouped by migration phase for easy import
# ============================================================================

ANALYSIS_TOOLS = [
    scan_maven_pom,
    scan_gradle_build,
    analyze_spring_properties,
    detect_database_type,
    extract_api_endpoints,
    analyze_react_app,
]

INFRASTRUCTURE_TOOLS = [
    check_gcloud_auth,
    enable_gcp_apis,
    create_artifact_registry,
    setup_firebase_project,
    configure_iam_permissions,
]

DATABASE_TOOLS = [
    create_cloud_sql_instance,
    detect_database_type,
]

BACKEND_DEPLOYMENT_TOOLS = [
    write_dockerfile,
    build_docker_image,
    push_docker_image,
    deploy_to_cloud_run,
    update_cors_origins,
]

FRONTEND_DEPLOYMENT_TOOLS = [
    configure_frontend_env,
    install_npm_dependencies,
    build_frontend,
    deploy_to_firebase,
]

ALL_TOOLS = list(set(
    ANALYSIS_TOOLS
    + INFRASTRUCTURE_TOOLS
    + DATABASE_TOOLS
    + BACKEND_DEPLOYMENT_TOOLS
    + FRONTEND_DEPLOYMENT_TOOLS
))
