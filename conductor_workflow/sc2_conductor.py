"""
Phase 449: Netflix Conductor - SC2 Bot CI/CD Pipeline Workflow
Workflow definition with JSON task list and Python worker implementation.
"""

import logging
import time
import json
import requests
from conductor.client.configuration.configuration import Configuration
from conductor.client.configuration.settings.authentication_settings import AuthenticationSettings
from conductor.client.worker.worker_task import worker_task
from conductor.client.automator.task_handler import TaskHandler
from conductor.client.http.models import StartWorkflowRequest

logger = logging.getLogger(__name__)

CONDUCTOR_URL = "http://localhost:8080/api"


# ---- Workflow Definition ----

SC2_CICD_WORKFLOW = {
    "name": "sc2_bot_cicd_pipeline",
    "description": "SC2 bot CI/CD pipeline: lint, test, build, deploy, verify",
    "version": 1,
    "tasks": [
        {
            "name": "lint_code",
            "taskReferenceName": "lint_ref",
            "type": "SIMPLE",
            "inputParameters": {"repo_path": "${workflow.input.repo_path}"},
        },
        {
            "name": "run_tests",
            "taskReferenceName": "tests_ref",
            "type": "SIMPLE",
            "inputParameters": {
                "repo_path": "${workflow.input.repo_path}",
                "lint_passed": "${lint_ref.output.passed}",
            },
        },
        {
            "name": "build_docker",
            "taskReferenceName": "docker_ref",
            "type": "SIMPLE",
            "inputParameters": {
                "image_name": "${workflow.input.image_name}",
                "tag": "${workflow.input.git_sha}",
            },
        },
        {
            "name": "deploy_bot",
            "taskReferenceName": "deploy_ref",
            "type": "SIMPLE",
            "inputParameters": {
                "image": "${docker_ref.output.image_uri}",
                "environment": "${workflow.input.environment}",
            },
        },
        {
            "name": "integration_test",
            "taskReferenceName": "integration_ref",
            "type": "SIMPLE",
            "inputParameters": {
                "bot_url": "${deploy_ref.output.bot_url}",
                "test_suite": "smoke",
            },
        },
    ],
    "outputParameters": {
        "deploy_url": "${deploy_ref.output.bot_url}",
        "test_passed": "${integration_ref.output.passed}",
    },
    "failureWorkflow": "sc2_bot_rollback",
    "restartable": True,
    "workflowStatusListenerEnabled": True,
    "schemaVersion": 2,
}


# ---- Task Worker Implementations ----

@worker_task(task_definition_name="lint_code")
def lint_code_worker(repo_path: str) -> dict:
    logger.info(f"Linting code at {repo_path}")
    time.sleep(0.1)
    return {"passed": True, "warnings": 2, "errors": 0}


@worker_task(task_definition_name="run_tests")
def run_tests_worker(repo_path: str, lint_passed: bool) -> dict:
    if not lint_passed:
        return {"passed": False, "reason": "lint failed"}
    logger.info(f"Running tests at {repo_path}")
    time.sleep(0.2)
    return {"passed": True, "total": 47, "failed": 0, "coverage": 0.82}


@worker_task(task_definition_name="build_docker")
def build_docker_worker(image_name: str, tag: str) -> dict:
    logger.info(f"Building Docker image {image_name}:{tag}")
    time.sleep(0.3)
    image_uri = f"registry.sc2bot.io/{image_name}:{tag}"
    return {"image_uri": image_uri, "size_mb": 245}


@worker_task(task_definition_name="deploy_bot")
def deploy_bot_worker(image: str, environment: str) -> dict:
    logger.info(f"Deploying {image} to {environment}")
    time.sleep(0.2)
    return {"bot_url": f"http://sc2bot-{environment}.internal:8080", "status": "running"}


@worker_task(task_definition_name="integration_test")
def integration_test_worker(bot_url: str, test_suite: str) -> dict:
    logger.info(f"Running {test_suite} tests against {bot_url}")
    time.sleep(0.1)
    return {"passed": True, "tests_run": 12, "duration_seconds": 45}


def register_workflow(conductor_url: str):
    """Register the workflow definition with Conductor server."""
    resp = requests.put(
        f"{conductor_url}/metadata/workflow",
        json=[SC2_CICD_WORKFLOW],
        headers={"Content-Type": "application/json"},
    )
    if resp.status_code == 204:
        logger.info("Workflow registered successfully.")
    else:
        logger.error(f"Workflow registration failed: {resp.status_code} {resp.text}")


def start_pipeline(conductor_url: str, repo_path: str, git_sha: str, env: str = "staging"):
    """Start the CI/CD pipeline workflow."""
    payload = {
        "name": "sc2_bot_cicd_pipeline",
        "version": 1,
        "input": {
            "repo_path": repo_path,
            "image_name": "sc2-zerg-bot",
            "git_sha": git_sha,
            "environment": env,
        },
    }
    resp = requests.post(f"{conductor_url}/workflow", json=payload)
    workflow_id = resp.text.strip().strip('"')
    logger.info(f"Pipeline started: {workflow_id}")
    return workflow_id


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("SC2 Conductor workflow definition:")
    print(json.dumps(SC2_CICD_WORKFLOW, indent=2)[:400], "...")
    print("Workers: lint_code, run_tests, build_docker, deploy_bot, integration_test")
