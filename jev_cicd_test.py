import os


USE_FIXTURE = os.environ.get("TYPESAFE_USE_FIXTURE") == "1"

state = {
    "pipeline": "SUCCESS",
    "gitleaks": "PASS",
    "semgrep": "PASS",
    "trivy_critical": 0,
    "replicas": 2,
    "cpu_utilization_percent": 3,
    "memory_utilization_percent": 7.42,
}

questions = {
    "deployment_decision": {
        "type": "choice",
        "instructions": "Should this CI/CD deployment proceed?",
        "criteria": {
            "approve": "Deployment is safe to proceed.",
            "review": "Deployment requires human review.",
            "reject": "Deployment should not proceed.",
        },
    }
}


# Official TypeSafe fixture pattern:
# this is simulated and does NOT call the real Jev API.
FIXTURE_RESPONSE = {
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


def call_jev():
    if USE_FIXTURE:
        print("[SIMULATED] TYPESAFE_USE_FIXTURE=1")
        return FIXTURE_RESPONSE

    raise RuntimeError(
        "Live Jev API requires TYPESAFE_API_KEY and available TypeSafe credits."
    )


result = call_jev()

print("CI/CD STATE:")
print(state)

print("\nJEV DECISION:")
print(result)
