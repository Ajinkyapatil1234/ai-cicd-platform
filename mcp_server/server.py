import os
import json
import re
import base64
import requests
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer
from google import genai


# Load credentials from mcp_server/.env
load_dotenv(Path(__file__).with_name(".env"))


mcp = MCPServer("AI-CI/CD-MCP")


@mcp.tool()
def get_project_status() -> str:
    """Return the current status of the AI CI/CD project."""
    return "AI CI/CD MCP server is running successfully."


@mcp.tool()
def get_kubernetes_status() -> str:
    """Return the current Kubernetes deployment and pod status."""
    try:
        import subprocess

        result = subprocess.run(
            [
                "kubectl",
                "--kubeconfig=/home/ajinkya/.kube/config",
                "get",
                "deployment",
                "ai-cicd-demo",
                "-o",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode != 0:
            return json.dumps(
                {
                    "status": "error",
                    "message": result.stderr.strip(),
                },
                indent=2,
            )

        deployment = json.loads(result.stdout)

        desired = deployment["spec"].get("replicas", 0)
        ready = deployment["status"].get("readyReplicas", 0)
        available = deployment["status"].get("availableReplicas", 0)

        pod_result = subprocess.run(
            [
                "kubectl",
                "--kubeconfig=/home/ajinkya/.kube/config",
                "get",
                "pods",
                "-l",
                "app=ai-cicd-demo",
                "-o",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )

        pods = []

        if pod_result.returncode == 0:
            pod_data = json.loads(pod_result.stdout)

            for pod in pod_data.get("items", []):
                pods.append(
                    {
                        "name": pod["metadata"]["name"],
                        "status": pod["status"].get("phase"),
                    }
                )

        health = (
            "HEALTHY"
            if desired == ready == available and desired > 0
            else "UNHEALTHY"
        )

        return json.dumps(
            {
                "deployment": "ai-cicd-demo",
                "desired_replicas": desired,
                "ready_replicas": ready,
                "available_replicas": available,
                "current_replicaset_hash": deployment["metadata"].get(
                    "annotations", {}
                ).get("deployment.kubernetes.io/revision"),
                "pods": pods,
                "health": health,
            },
            indent=2,
        )

    except Exception as exc:
        return json.dumps(
            {
                "status": "error",
                "message": str(exc),
            },
            indent=2,
        )


@mcp.tool()
def check_jenkins_env() -> str:
    """Check whether Jenkins credentials are visible to the MCP server."""
    return json.dumps(
        {
            "jenkins_user_set": bool(os.environ.get("JENKINS_USER")),
            "jenkins_token_set": bool(os.environ.get("JENKINS_API_TOKEN")),
            "jenkins_user": os.environ.get("JENKINS_USER"),
        },
        indent=2,
    )


@mcp.tool()
def get_pipeline_security_status() -> str:
    """Return the latest Jenkins CI/CD and security scan status."""

    try:
        username = os.environ.get("JENKINS_USER")
        api_token = os.environ.get("JENKINS_API_TOKEN")

        if not username or not api_token:
            return json.dumps(
                {
                    "status": "error",
                    "message": "Jenkins credentials are not configured.",
                },
                indent=2,
            )

        # Build Basic Authentication header.
        credentials = f"{username}:{api_token}"

        encoded_credentials = base64.b64encode(
            credentials.encode()
        ).decode()

        headers = {
            "Authorization": f"Basic {encoded_credentials}"
        }

        # Jenkins latest build API.
        api_url = (
            "http://localhost:8080/"
            "job/ai-cicd-pipeline/"
            "lastBuild/api/json"
        )

        response = requests.get(
            api_url,
            headers=headers,
            timeout=10,
        )

        response.raise_for_status()

        build = response.json()

        build_number = build.get("number")
        build_result = build.get("result")

        # Jenkins console output.
        console_url = (
            f"http://localhost:8080/job/ai-cicd-pipeline/"
            f"{build_number}/consoleText"
        )

        response = requests.get(
            console_url,
            headers=headers,
            timeout=15,
        )

        response.raise_for_status()

        console_text = response.text

        console_lower = console_text.lower()

        # Gitleaks.
        gitleaks_pass = "no leaks found" in console_lower

        # Semgrep.
        semgrep_match = re.search(
            r"Findings:\s*(\d+)\s*\((\d+)\s*blocking\)",
            console_text,
        )

        semgrep_findings = (
            int(semgrep_match.group(1))
            if semgrep_match
            else None
        )

        semgrep_blocking = (
            int(semgrep_match.group(2))
            if semgrep_match
            else None
        )

        # Trivy.
        trivy_matches = re.findall(
            r"Total:\s*(\d+)\s*\(HIGH:\s*(\d+),\s*CRITICAL:\s*(\d+)\)",
            console_text,
        )

        trivy_results = []

        for total, high, critical in trivy_matches:
            trivy_results.append(
                {
                    "total": int(total),
                    "high": int(high),
                    "critical": int(critical),
                }
            )

        # Overall pipeline status.
        pipeline_pass = build_result == "SUCCESS"

        return json.dumps(
            {
                "status": "success",
                "pipeline": {
                    "build_number": build_number,
                    "result": build_result,
                    "passed": pipeline_pass,
                },
                "security": {
                    "gitleaks": {
                        "passed": gitleaks_pass,
                        "secrets_found": not gitleaks_pass,
                    },
                    "semgrep": {
                        "findings": semgrep_findings,
                        "blocking": semgrep_blocking,
                        "passed": semgrep_blocking == 0,
                    },
                    "trivy": trivy_results,
                },
            },
            indent=2,
        )

    except requests.HTTPError as exc:
        status_code = (
            exc.response.status_code
            if exc.response is not None
            else "unknown"
        )

        return json.dumps(
            {
                "status": "error",
                "message": f"HTTP Error {status_code}: {exc}",
            },
            indent=2,
        )

    except Exception as exc:
        return json.dumps(
            {
                "status": "error",
                "message": str(exc),
            },
            indent=2,
        )


@mcp.tool()
def analyze_ci_cd_with_gemini() -> str:
    """Analyze the latest CI/CD, security, and Kubernetes status using Gemini."""

    try:
        gemini_api_key = os.environ.get("GEMINI_API_KEY")

        if not gemini_api_key:
            return json.dumps(
                {
                    "status": "error",
                    "message": "Gemini API key is not configured.",
                },
                indent=2,
            )

        # Collect evidence from our existing MCP tools.
        security_status = get_pipeline_security_status()
        kubernetes_status = get_kubernetes_status()

        prompt = f"""
You are an AI CI/CD security and reliability analyst.

Analyze the following real CI/CD evidence collected by an MCP server.

JENKINS SECURITY STATUS:
{security_status}

KUBERNETES STATUS:
{kubernetes_status}

Provide a concise engineering analysis with exactly these sections:

1. Pipeline Status
2. Security Findings
3. Kubernetes Health
4. Risks
5. Recommended Actions

Important rules:
- Do not invent findings.
- Distinguish HIGH vulnerabilities from CRITICAL vulnerabilities.
- Do not claim a vulnerability is exploitable unless the evidence supports it.
- Do not override deterministic security gates.
- Recommendations should prioritize security, reliability, and cost effectiveness.
"""

        client = genai.Client(api_key=gemini_api_key)

        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
        )

        return json.dumps(
            {
                "status": "success",
                "model": "gemini-3.5-flash",
                "analysis": response.text,
            },
            indent=2,
        )

    except Exception as exc:
        return json.dumps(
            {
                "status": "error",
                "message": str(exc),
            },
            indent=2,
        )


@mcp.tool()
def get_resource_cost_analysis() -> str:
    """Analyze Kubernetes resource requests versus actual runtime usage."""

    try:
        import subprocess

        kubeconfig = "/home/ajinkya/.kube/config"

        # Get configured resource requests/limits
        deployment_result = subprocess.run(
            [
                "kubectl",
                f"--kubeconfig={kubeconfig}",
                "get",
                "deployment",
                "ai-cicd-demo",
                "-o",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if deployment_result.returncode != 0:
            return json.dumps(
                {
                    "status": "error",
                    "message": deployment_result.stderr.strip(),
                },
                indent=2,
            )

        deployment = json.loads(deployment_result.stdout)

        containers = deployment["spec"]["template"]["spec"]["containers"]

        configured_cpu_request = 0
        configured_memory_request = 0
        configured_cpu_limit = 0
        configured_memory_limit = 0

        for container in containers:
            resources = container.get("resources", {})

            requests = resources.get("requests", {})
            limits = resources.get("limits", {})

            configured_cpu_request += int(
                requests.get("cpu", "0m").replace("m", "")
            )

            configured_memory_request += int(
                requests.get("memory", "0Mi").replace("Mi", "")
            )

            configured_cpu_limit += int(
                limits.get("cpu", "0m").replace("m", "")
            )

            configured_memory_limit += int(
                limits.get("memory", "0Mi").replace("Mi", "")
            )

        replicas = deployment["spec"].get("replicas", 0)

        configured_cpu_request *= replicas
        configured_memory_request *= replicas
        configured_cpu_limit *= replicas
        configured_memory_limit *= replicas

        # Get actual runtime usage
        metrics_result = subprocess.run(
            [
                "kubectl",
                f"--kubeconfig={kubeconfig}",
                "top",
                "pods",
                "-l",
                "app=ai-cicd-demo",
                "--no-headers",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if metrics_result.returncode != 0:
            return json.dumps(
                {
                    "status": "error",
                    "message": metrics_result.stderr.strip(),
                },
                indent=2,
            )

        actual_cpu = 0
        actual_memory = 0
        pod_usage = []

        for line in metrics_result.stdout.strip().splitlines():
            parts = line.split()

            if len(parts) >= 3:
                pod_name = parts[0]
                cpu = parts[1]
                memory = parts[2]

                cpu_m = int(cpu.replace("m", ""))
                memory_mi = int(memory.replace("Mi", ""))

                actual_cpu += cpu_m
                actual_memory += memory_mi

                pod_usage.append(
                    {
                        "pod": pod_name,
                        "cpu": cpu,
                        "memory": memory,
                    }
                )

        cpu_utilization = (
            round((actual_cpu / configured_cpu_request) * 100, 2)
            if configured_cpu_request
            else 0
        )

        memory_utilization = (
            round((actual_memory / configured_memory_request) * 100, 2)
            if configured_memory_request
            else 0
        )

        return json.dumps(
            {
                "status": "success",
                "replicas": replicas,
                "configured": {
                    "cpu_request": f"{configured_cpu_request}m",
                    "memory_request": f"{configured_memory_request}Mi",
                    "cpu_limit": f"{configured_cpu_limit}m",
                    "memory_limit": f"{configured_memory_limit}Mi",
                },
                "actual_usage": {
                    "cpu": f"{actual_cpu}m",
                    "memory": f"{actual_memory}Mi",
                    "pods": pod_usage,
                },
                "utilization": {
                    "cpu_vs_request_percent": cpu_utilization,
                    "memory_vs_request_percent": memory_utilization,
                },
                "optimization": {
                    "cpu_overprovisioned": cpu_utilization < 50,
                    "memory_overprovisioned": memory_utilization < 50,
                    "recommendation": (
                        "Workload appears significantly underutilized. "
                        "Consider right-sizing resource requests while "
                        "maintaining an operational safety margin."
                    )
                    if cpu_utilization < 50 or memory_utilization < 50
                    else "Resource utilization appears reasonable.",
                },
                "cost_note": (
                    "This is a local Minikube resource analysis. "
                    "No real cloud cost savings are claimed."
                ),
            },
            indent=2,
        )

    except Exception as exc:
        return json.dumps(
            {
                "status": "error",
                "message": str(exc),
            },
            indent=2,
        )


@mcp.tool()
def get_jev_deployment_decision() -> str:
    """
    Use Jev for structured CI/CD deployment decisioning.

    Current implementation supports TypeSafe fixture mode for local testing.
    Live Jev requires a valid TYPESAFE_API_KEY and available TypeSafe credits.
    """

    pipeline_raw = get_pipeline_security_status()
    pipeline_data = json.loads(pipeline_raw)

    if pipeline_data.get("status") != "success":
        return json.dumps(
            {
                "status": "error",
                "message": "Unable to retrieve pipeline/security status.",
                "details": pipeline_data,
            },
            indent=2,
        )

    cost_raw = get_resource_cost_analysis()
    cost_data = json.loads(cost_raw)

    if cost_data.get("status") != "success":
        return json.dumps(
            {
                "status": "error",
                "message": "Unable to retrieve Kubernetes resource status.",
                "details": cost_data,
            },
            indent=2,
        )

    trivy_results = pipeline_data["security"].get("trivy", [])

    trivy_critical = sum(
        item.get("critical", 0)
        for item in trivy_results
    )

    state = {
        "pipeline": pipeline_data["pipeline"]["result"],
        "gitleaks": (
            "PASS"
            if pipeline_data["security"]["gitleaks"]["passed"]
            else "FAIL"
        ),
        "semgrep": (
            "PASS"
            if pipeline_data["security"]["semgrep"]["passed"]
            else "FAIL"
        ),
        "trivy_critical": trivy_critical,
        "replicas": cost_data["replicas"],
        "cpu_utilization_percent": cost_data["utilization"][
            "cpu_vs_request_percent"
        ],
        "memory_utilization_percent": cost_data["utilization"][
            "memory_vs_request_percent"
        ],
    }

    use_fixture = os.environ.get("TYPESAFE_USE_FIXTURE") == "1"

    if use_fixture:
        result = {
            "model": "jev-1.13.0",
            "answers": {
                "deployment_decision": {
                    "type": "choice",
                    "choice": "approve",
                    "confidence": 0.78,
                    "probabilities": {
                        "approve": 0.85,
                        "review": 0.10,
                        "reject": 0.05,
                    },
                }
            },
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
            },
        }

        return json.dumps(
            {
                "status": "success",
                "mode": "SIMULATED",
                "state": state,
                "jev": result,
            },
            indent=2,
        )

    api_key = os.environ.get("TYPESAFE_API_KEY")

    if not api_key:
        return json.dumps(
            {
                "status": "unavailable",
                "mode": "LIVE",
                "message": (
                    "TYPESAFE_API_KEY is not configured. "
                    "Live Jev requires an API key and available TypeSafe credits."
                ),
            },
            indent=2,
        )

    try:
        from typesafe_sdk import TypeSafeClient, Choice

        client = TypeSafeClient(
            api_key=api_key,
            model="jev-latest",
        )

        questions = {
            "deployment_decision": Choice(
                instructions="Should this CI/CD deployment proceed?",
                criteria={
                    "approve": "Deployment is safe to proceed.",
                    "review": "Deployment requires human review.",
                    "reject": "Deployment should not proceed.",
                },
            )
        }

        result = client.system_one(
            state=state,
            questions=questions,
        )

        return json.dumps(
            {
                "status": "success",
                "mode": "LIVE",
                "state": state,
                "jev": result.model_dump(),
            },
            indent=2,
        )

    except Exception as exc:
        return json.dumps(
            {
                "status": "error",
                "mode": "LIVE",
                "message": str(exc),
            },
            indent=2,
        )


@mcp.tool()
def run_ai_cicd_decision() -> str:
    """
    Run the end-to-end AI CI/CD decision workflow.

    Deterministic security and pipeline failures always block deployment.
    Gemini provides analysis and Jev provides structured decisioning.
    """

    try:
        # 1. Get deterministic Jenkins and security status.
        pipeline_result = json.loads(
            get_pipeline_security_status()
        )

        # Hard safety gate.
        if pipeline_result.get("status") != "success":
            return json.dumps(
                {
                    "status": "blocked",
                    "reason": "Pipeline status could not be verified.",
                    "pipeline": pipeline_result,
                },
                indent=2,
            )

        pipeline = pipeline_result.get("pipeline", {})
        security = pipeline_result.get("security", {})

        gitleaks_passed = security.get(
            "gitleaks", {}
        ).get("passed", False)

        semgrep_blocking = security.get(
            "semgrep", {}
        ).get("blocking", 0)

        trivy_results = security.get(
            "trivy", []
        )

        trivy_critical = sum(
            item.get("critical", 0)
            for item in trivy_results
        )

        # Never allow AI to override deterministic security gates.
        #
        # IMPORTANT:
        # Do not check pipeline.get("result") here.
        # The MCP decision runs inside the same Jenkins build,
        # so that build cannot be SUCCESS until this stage finishes.
        if (
            not gitleaks_passed
            or semgrep_blocking != 0
            or trivy_critical != 0
        ):
            return json.dumps(
                {
                    "status": "blocked",
                    "reason": "Deterministic CI/CD security gate failed.",
                    "pipeline": pipeline_result,
                },
                indent=2,
            )

        # 2. Get current Kubernetes resource usage.
        cost_result = json.loads(
            get_resource_cost_analysis()
        )

        if cost_result.get("status") != "success":
            return json.dumps(
                {
                    "status": "blocked",
                    "reason": "Kubernetes resource analysis failed.",
                    "cost_analysis": cost_result,
                },
                indent=2,
            )

        # 3. Get Gemini analysis.
        gemini_result = json.loads(
            analyze_ci_cd_with_gemini()
        )

        gemini_available = (
            gemini_result.get("status") == "success"
        )

        # 4. Get structured Jev decision.
        jev_result = json.loads(
            get_jev_deployment_decision()
        )

        # 5. Extract Jev decision.
        jev_answer = (
            jev_result
            .get("jev", {})
            .get("answers", {})
            .get("deployment_decision", {})
        )

        jev_choice = jev_answer.get("choice")
        jev_confidence = jev_answer.get("confidence", 0)

        final_decision = (
            "APPROVE"
            if jev_choice == "approve"
            and jev_confidence >= 0.70
            else "REVIEW"
        )

        return json.dumps(
            {
                "status": "success",
                "final_decision": final_decision,
                "pipeline": pipeline_result,
                "resource_analysis": cost_result,
                "gemini": gemini_result,
                "jev": jev_result,
                "decision_policy": {
                    "security_gates_passed": True,
                    "jev_confidence_threshold": 0.70,
                    "gemini_status": (
                        "AVAILABLE"
                        if gemini_available
                        else "ANALYSIS_UNAVAILABLE"
                    ),
                },
            },
            indent=2,
        )

    except Exception as exc:
        return json.dumps(
            {
                "status": "error",
                "message": str(exc),
            },
            indent=2,
        )


if __name__ == "__main__":
    mcp.run()
