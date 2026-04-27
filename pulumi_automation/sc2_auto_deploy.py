# SC2 Bot - Pulumi Automation API
# Programmatic IaC: create/update stacks from Python code

import pulumi
import pulumi_aws as aws
from pulumi import automation as auto
from typing import Optional
import os, sys


# -----------------------------------------------
# Inline Pulumi Program: SC2 Bot Infrastructure
# -----------------------------------------------
def sc2_pulumi_program():
    """Inline Pulumi program defining SC2 bot infrastructure."""
    env = pulumi.get_stack()

    # --- S3: Replay storage ---
    replay_bucket = aws.s3.Bucket(
        "sc2-replays",
        bucket=f"sc2-bot-replays-{env}",
        acl="private",
        versioning=aws.s3.BucketVersioningArgs(enabled=True),
        lifecycle_rules=[
            aws.s3.BucketLifecycleRuleArgs(
                enabled=True,
                expiration=aws.s3.BucketLifecycleRuleExpirationArgs(days=365),
            )
        ],
        tags={"Project": "SC2Bot", "Env": env},
    )

    # --- EKS Cluster ---
    eks_cluster = aws.eks.Cluster(
        "sc2-eks",
        name=f"sc2-bot-{env}",
        role_arn=os.environ.get("EKS_ROLE_ARN", "arn:aws:iam::123:role/eks-role"),
        vpc_config=aws.eks.ClusterVpcConfigArgs(
            subnet_ids=["subnet-abc123", "subnet-def456"],
            endpoint_public_access=True,
        ),
        version="1.30",
        tags={"Project": "SC2Bot"},
    )

    # --- RDS Postgres ---
    db = aws.rds.Instance(
        "sc2-db",
        identifier=f"sc2-bot-db-{env}",
        engine="postgres",
        engine_version="16.2",
        instance_class="db.t3.medium",
        allocated_storage=100,
        db_name="sc2bot",
        username="sc2admin",
        password=os.environ.get("DB_PASSWORD", "changeme"),
        skip_final_snapshot=True,
        multi_az=(env == "production"),
        tags={"Project": "SC2Bot"},
    )

    # --- ECR Repository ---
    ecr = aws.ecr.Repository(
        "sc2-ecr",
        name="sc2-bot",
        image_tag_mutability="IMMUTABLE",
        image_scanning_configuration=aws.ecr.RepositoryImageScanningConfigurationArgs(
            scan_on_push=True,
        ),
    )

    # --- Outputs ---
    pulumi.export("replay_bucket", replay_bucket.bucket)
    pulumi.export("eks_cluster", eks_cluster.name)
    pulumi.export("db_endpoint", db.endpoint)
    pulumi.export("ecr_url", ecr.repository_url)


# -----------------------------------------------
# Automation API: Stack Management
# -----------------------------------------------
def deploy(env: str = "production", preview_only: bool = False):
    """Create or select a stack and deploy SC2 bot infrastructure."""
    project = "sc2-bot-infra"
    stack_name = f"{project}/{env}"

    print(f"[Pulumi Auto] Initializing stack: {stack_name}")
    stack = auto.create_or_select_stack(
        stack_name=stack_name,
        project_name=project,
        program=sc2_pulumi_program,
    )

    # Configure AWS region
    stack.set_config("aws:region", auto.ConfigValue("us-east-1"))
    stack.set_config("aws:skipCredentialsValidation", auto.ConfigValue("false"))

    print(f"[Pulumi Auto] Refreshing state...")
    stack.refresh(on_output=print)

    if preview_only:
        print(f"[Pulumi Auto] Running preview (CI/PR mode)...")
        preview = stack.preview(on_output=print)
        print(f"[Pulumi Auto] Preview: {preview.change_summary}")
        return preview

    print(f"[Pulumi Auto] Deploying...")
    up_result = stack.up(on_output=print)
    print(f"[Pulumi Auto] Summary: {up_result.summary.result}")
    print(f"[Pulumi Auto] Outputs:")
    for k, v in up_result.outputs.items():
        print(f"  {k}: {v.value}")
    return up_result


def destroy(env: str):
    """Destroy SC2 bot infrastructure for a given environment."""
    project = "sc2-bot-infra"
    stack = auto.select_stack(
        stack_name=f"{project}/{env}",
        project_name=project,
        program=sc2_pulumi_program,
    )
    print(f"[Pulumi Auto] Destroying stack: {env}")
    stack.destroy(on_output=print)
    stack.workspace.remove_stack(f"{project}/{env}")
    print(f"[Pulumi Auto] Stack {env} destroyed and removed.")


# -----------------------------------------------
# CI/CD Integration Entry Point
# -----------------------------------------------
if __name__ == "__main__":
    env = os.environ.get("ENVIRONMENT", "staging")
    is_pr = os.environ.get("CI_PULL_REQUEST", "false") == "true"
    preview_only = is_pr  # preview on PR, full up on merge

    result = deploy(env=env, preview_only=preview_only)
    sys.exit(0)
