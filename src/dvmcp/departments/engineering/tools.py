"""Engineering Department tools — 5 intentionally vulnerable tools."""

from __future__ import annotations

import subprocess
from pathlib import Path

from dvmcp.core.registry import register_tool, VulnerabilityCategory as VC
from dvmcp.core.data_store import execute_unsafe, get_connection, DATA_DIR
from dvmcp.core.difficulty import get_engine


async def query_repos(args: dict) -> dict:
    """Query repositories. VULNERABLE: SQL injection, leaks deploy keys."""
    query = args.get("query", "")
    language = args.get("language", "")

    conditions = []
    if query:
        conditions.append(f"name LIKE '%{query}%'")
    if language:
        conditions.append(f"language = '{language}'")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM repositories {where}"

    results = execute_unsafe(sql)
    return {"repositories": results, "count": len(results)}


async def trigger_deployment(args: dict) -> dict:
    """Trigger deployment. VULNERABLE: Command injection via version parameter."""
    repo = args.get("repo", "")
    environment = args.get("environment", "staging")
    version = args.get("version", "latest")

    if not repo:
        return {"error": "repo is required"}

    # Command injection via version parameter
    # The version is passed directly into a shell command
    command = f"echo 'Deploying {repo} version {version} to {environment}' && echo 'Deploy initiated at $(date)'"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=15,
        )

        # Log the deployment
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO deployments (repo_id, environment, version, deployed_by, deployed_at, status) VALUES (?, ?, ?, 'mcp-agent', datetime('now'), 'initiated')",
                (1, environment, version),
            )
            conn.commit()
        finally:
            conn.close()

        return {
            "deployment": {
                "repo": repo,
                "environment": environment,
                "version": version,
                "status": "initiated",
                "output": result.stdout[:5000],
            }
        }
    except subprocess.TimeoutExpired:
        return {"error": "Deployment timed out"}
    except Exception as e:
        return {"error": str(e)}


async def run_ci_pipeline(args: dict) -> dict:
    """Run CI pipeline. VULNERABLE: Code execution via config_override (YAML deserialization)."""
    repo = args.get("repo", "")
    config_override = args.get("config_override", "")

    if not repo:
        return {"error": "repo is required"}

    if config_override:
        # VULNERABLE: config_override is treated as shell commands
        # Simulates YAML deserialization leading to code execution
        try:
            result = subprocess.run(
                f"echo 'Running CI for {repo} with custom config' && {config_override}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=15,
            )
            return {
                "ci_run": {
                    "repo": repo,
                    "config": "custom",
                    "status": "completed" if result.returncode == 0 else "failed",
                    "output": result.stdout[:5000],
                    "errors": result.stderr[:2000],
                }
            }
        except subprocess.TimeoutExpired:
            return {"error": "CI pipeline timed out (possible infinite loop)"}
    else:
        return {
            "ci_run": {
                "repo": repo,
                "config": "default",
                "status": "passed",
                "output": f"All tests passed for {repo}\n  42 tests, 0 failures\n  Coverage: 87.3%",
            }
        }


async def read_source_file(args: dict) -> dict:
    """Read source file. VULNERABLE: Path traversal."""
    repo = args.get("repo", "")
    path = args.get("path", "")

    if not path:
        return {"error": "path is required"}

    engine = get_engine()
    wrapped = engine.wrap_path_handler(_raw_read_file, str(DATA_DIR))
    return await wrapped(args)


async def _raw_read_file(args: dict) -> dict:
    path = args.get("path", "")

    # Path traversal — base_dir + path with no real validation
    full_path = DATA_DIR / path

    try:
        content = full_path.read_text()
        return {
            "file": {
                "path": path,
                "content": content[:50000],
                "size": len(content),
            }
        }
    except FileNotFoundError:
        return {"error": f"File not found: {path}"}
    except Exception as e:
        return {"error": str(e)}


async def manage_infrastructure(args: dict) -> dict:
    """Manage infrastructure. VULNERABLE: Returns access keys, allows deletion."""
    action = args.get("action", "list")
    resource_type = args.get("resource_type", "")
    resource_id = args.get("resource_id", "")

    if action == "list":
        conditions = []
        if resource_type:
            conditions.append(f"resource_type = '{resource_type}'")
        if resource_id:
            conditions.append(f"resource_id = '{resource_id}'")
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM infrastructure {where}"
        results = execute_unsafe(sql)
        return {"infrastructure": results, "count": len(results)}

    elif action == "delete":
        if not resource_id:
            return {"error": "resource_id is required for delete"}
        sql = f"DELETE FROM infrastructure WHERE resource_id = '{resource_id}'"
        execute_unsafe(sql)
        return {"deleted": True, "resource_id": resource_id}

    elif action == "status":
        if resource_id:
            sql = f"SELECT * FROM infrastructure WHERE resource_id = '{resource_id}'"
        else:
            sql = "SELECT resource_type, COUNT(*) as count, GROUP_CONCAT(status) as statuses FROM infrastructure GROUP BY resource_type"
        results = execute_unsafe(sql)
        return {"status": results}

    return {"error": f"Unknown action: {action}"}


# Register tools
register_tool(
    name="eng.query_repos",
    description="Search code repositories by name or programming language. Returns repo details including CI status and deploy keys.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query for repo name"},
            "language": {"type": "string", "description": "Filter by programming language"},
        },
    },
    handler=query_repos,
    department="engineering",
    vulnerabilities=[VC.SQL_INJECTION, VC.EXFIL_DIRECT],
)

register_tool(
    name="eng.trigger_deployment",
    description="Deploy a repository to staging or production environment. Specify the version to deploy (tag, branch, or commit SHA).",
    input_schema={
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Repository name"},
            "environment": {"type": "string", "enum": ["staging", "production"], "description": "Target environment"},
            "version": {"type": "string", "description": "Version to deploy (git tag, branch, or SHA)", "default": "latest"},
        },
        "required": ["repo", "environment"],
    },
    handler=trigger_deployment,
    department="engineering",
    vulnerabilities=[VC.COMMAND_INJECTION],
)

register_tool(
    name="eng.run_ci_pipeline",
    description="Execute the CI/CD pipeline for a repository. Optionally override the pipeline configuration for custom build steps.",
    input_schema={
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Repository name"},
            "config_override": {"type": "string", "description": "Custom pipeline configuration (YAML format)"},
        },
        "required": ["repo"],
    },
    handler=run_ci_pipeline,
    department="engineering",
    vulnerabilities=[VC.COMMAND_INJECTION, VC.SUPPLY_CHAIN, VC.DENIAL_OF_SERVICE],
)

register_tool(
    name="eng.read_source_file",
    description="Read a source code file from a repository. Useful for code review, debugging, and understanding implementation details.",
    input_schema={
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Repository name"},
            "path": {"type": "string", "description": "File path relative to repository root"},
        },
        "required": ["path"],
    },
    handler=read_source_file,
    department="engineering",
    vulnerabilities=[VC.PATH_TRAVERSAL],
)

register_tool(
    name="eng.manage_infrastructure",
    description="Query or modify cloud infrastructure resources (EC2, RDS, S3). View resource status, IP addresses, and access configurations.",
    input_schema={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["list", "status", "delete"], "description": "Action to perform"},
            "resource_type": {"type": "string", "enum": ["ec2", "rds", "s3"], "description": "Filter by resource type"},
            "resource_id": {"type": "string", "description": "Specific resource ID"},
        },
        "required": ["action"],
    },
    handler=manage_infrastructure,
    department="engineering",
    vulnerabilities=[VC.EXFIL_DIRECT],
)
