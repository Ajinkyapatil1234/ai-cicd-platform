# AI-Assisted CI/CD Platform

An AI-assisted CI/CD pipeline that combines automated testing, security scanning, AI-driven analysis, approval orchestration, and Kubernetes deployment.

**GitHub Repository:** [ai-cicd-platform](https://github.com/Ajinkyapatil1234/ai-cicd-platform)

## Overview

This project demonstrates how AI-assisted decision-making can be integrated into a DevSecOps workflow to improve deployment visibility and support safer releases.

The pipeline validates application code, scans for security issues, builds a Docker image, evaluates deployment readiness, and uses an approval workflow before deploying to Kubernetes.

## Architecture

```text
Developer
    |
    v
Jenkins CI/CD Pipeline
    |
    +--> Automated Tests (pytest)
    |
    +--> Secret Scanning (Gitleaks)
    |
    +--> Static Analysis (Semgrep)
    |
    +--> Docker Image Build
    |
    +--> Vulnerability Scanning (Trivy)
    |
    +--> MCP Server
    |       |
    |       +--> Jenkins Status
    |       +--> Kubernetes Resource Analysis
    |       +--> Gemini AI Analysis
    |       +--> Jev Decision (Simulated)
    |
    v
n8n Approval Workflow
    |
    +--> APPROVED
    |
    +--> REVIEW_OR_REJECT
    |
    v
Kubernetes Deployment
    |
    v
Rollout Verification
```

## Technology Stack

| Category | Technologies |
|---|---|
| CI/CD | Jenkins |
| Application | Python, Flask |
| Containerization | Docker |
| Orchestration | Kubernetes, Minikube |
| Security | Gitleaks, Semgrep, Trivy |
| AI Analysis | Google Gemini |
| AI Integration | Model Context Protocol (MCP) |
| Workflow Automation | n8n |
| Testing | pytest |
| Scripting | Python, Bash |

## Key Features

- **Automated CI/CD:** Jenkins orchestrates testing, scanning, image building, approval, and deployment.
- **Automated testing:** pytest validates application behavior before deployment.
- **Secret detection:** Gitleaks scans for accidentally committed credentials.
- **Static application security testing:** Semgrep checks source code for security issues.
- **Container vulnerability scanning:** Trivy generates vulnerability reports and enforces the configured security policy.
- **AI-assisted analysis:** Gemini analyzes CI/CD and Kubernetes status to provide additional context for deployment decisions.
- **MCP integration:** An MCP server exposes tools for retrieving pipeline information and analyzing Kubernetes resources.
- **Approval orchestration:** n8n processes the decision returned by the MCP workflow.
- **Kubernetes deployment:** The application runs with two replicas, resource requests and limits, and health probes.
- **Container hardening:** The deployment uses a non-root user, disables privilege escalation, drops Linux capabilities, and enables the default seccomp profile.

## Security Policy

The pipeline includes multiple security checks:

1. Gitleaks for secret detection.
2. Semgrep for static code analysis.
3. Trivy for container image vulnerability scanning.

The current Trivy gate blocks HIGH and CRITICAL vulnerabilities when a fix is available. Unfixed findings are documented in the generated report and are not automatically blocked by this demo policy.

**Note:** Passing the configured gate does not mean the image is vulnerability-free. A production pipeline should apply an explicitly approved vulnerability policy, including handling of unfixed critical vulnerabilities.

## AI Decision Workflow

The MCP server integrates with Gemini for AI-assisted analysis of pipeline and Kubernetes status. The decision is then sent through an n8n workflow to determine whether the pipeline can proceed.

The current Jev decision component runs in **simulated mode**. Live Jev decisions require a configured API key and available service credits.

## Kubernetes Security and Reliability

The deployment configuration includes:

- Two application replicas.
- CPU and memory requests and limits.
- Readiness and liveness probes on `/health`.
- Non-root execution using UID `1000`.
- Runtime-default seccomp profile.
- Disabled privilege escalation.
- All Linux capabilities dropped.

These controls demonstrate basic container security and application health monitoring.

## Running Locally

### Prerequisites

- Docker
- Python 3.10
- kubectl
- Minikube
- Jenkins
- n8n
- Required API credentials for enabled integrations

### 1. Clone the repository

```bash
git clone https://github.com/Ajinkyapatil1234/ai-cicd-platform.git
cd ai-cicd-platform
```

### 2. Create a Python virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the tests

```bash
pytest -v
```

### 4. Build the Docker image

```bash
docker build -t ai-cicd-demo:1.0 .
```

### 5. Deploy to Minikube

Start Minikube and ensure the image is available inside its container runtime. Then apply the Kubernetes manifests:

```bash
kubectl apply -f k8s/
kubectl rollout status deployment/ai-cicd-demo --timeout=120s
kubectl get pods -l app=ai-cicd-demo
```

To test the application locally:

```bash
kubectl port-forward deployment/ai-cicd-demo 8081:8080
```

In another terminal:

```bash
curl -i http://127.0.0.1:8081/health
```

Expected response:

```json
{"status":"healthy"}
```

### 6. Configure integrations

Configure Jenkins, the MCP server, and n8n according to your local environment. Store credentials in environment variables rather than committing them to source control.

Required variables depend on the integrations you enable and may include:

- `JENKINS_USER`
- `JENKINS_API_TOKEN`
- `GEMINI_API_KEY`
- `TYPESAFE_API_KEY` — required only for live Jev integration

Do not commit `.env` files, API keys, access tokens, or other credentials.

## Project Structure

```text
ai-cicd-platform/
├── app/
│   └── main.py
├── k8s/
│   ├── deployment.yaml
│   └── service.yaml
├── mcp_server/
│   ├── __init__.py
│   ├── server.py
│   └── test_client.py
├── tests/
├── Dockerfile
├── .dockerignore
├── .gitignore
├── jev_cicd_test.py
├── requirements.txt
└── triage.py
```

## Project Outcome

This project demonstrates the integration of CI/CD automation, container security, AI-assisted analysis, workflow-based approval, and Kubernetes deployment verification in a single development workflow.

It is intended as a practical DevSecOps portfolio project and a foundation for further improvements, including stricter vulnerability policies, automated reporting, and production-grade deployment controls.

## Author

**Ajinkya Patil**

GitHub: [Ajinkyapatil1234](https://github.com/Ajinkyapatil1234)
