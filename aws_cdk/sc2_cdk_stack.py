# SC2 Bot - AWS CDK (Python) Infrastructure Stack
# SC2BotInfraStack with EKS, RDS, S3, ECR, and custom SC2BotService construct

import os

from constructs import Construct

import aws_cdk as cdk
from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_eks as eks
from aws_cdk import aws_iam as iam
from aws_cdk import aws_rds as rds
from aws_cdk import aws_s3 as s3


# ========================================
# Custom Construct: SC2BotService
# ========================================
class SC2BotService(Construct):
    """High-level construct encapsulating all SC2 bot compute resources."""

    def __init__(
        self, scope: Construct, id: str, cluster: eks.Cluster, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # ECR repository for SC2 bot Docker images
        self.repo = ecr.Repository(
            self,
            "SC2BotRepo",
            repository_name="sc2-bot",
            image_tag_mutability=ecr.TagMutability.IMMUTABLE,
            image_scan_on_push=True,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # EKS managed node group for SC2 workloads
        self.node_group = cluster.add_nodegroup_capacity(
            "SC2Workers",
            instance_types=[ec2.InstanceType("t3.xlarge")],
            min_size=1,
            max_size=10,
            desired_size=3,
            disk_size=50,
            labels={"workload": "sc2-bot"},
        )

        CfnOutput(scope, "ECRRepositoryURL", value=self.repo.repository_uri)


# ========================================
# Main Stack: SC2BotInfraStack
# ========================================
class SC2BotInfraStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        env_name = self.node.try_get_context("env") or "production"

        # --- VPC ---
        vpc = ec2.Vpc(
            self,
            "SC2VPC",
            max_azs=3,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
            ],
        )

        # --- EKS Cluster ---
        eks_cluster = eks.Cluster(
            self,
            "SC2EKS",
            cluster_name=f"sc2-bot-{env_name}",
            version=eks.KubernetesVersion.V1_30,
            vpc=vpc,
            default_capacity=0,
            endpoint_access=eks.EndpointAccess.PUBLIC,
        )

        # --- Custom SC2BotService construct ---
        sc2_service = SC2BotService(self, "SC2BotService", cluster=eks_cluster)

        # --- RDS Postgres ---
        db_sg = ec2.SecurityGroup(self, "DBSG", vpc=vpc, description="SC2 Bot RDS SG")
        db_sg.add_ingress_rule(ec2.Peer.ipv4(vpc.vpc_cidr_block), ec2.Port.tcp(5432))

        db_instance = rds.DatabaseInstance(
            self,
            "SC2DB",
            database_name="sc2bot",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16_2
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3, ec2.InstanceSize.MEDIUM
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[db_sg],
            multi_az=(env_name == "production"),
            allocated_storage=100,
            removal_policy=RemovalPolicy.SNAPSHOT,
        )

        # --- S3 Replay Bucket ---
        replay_bucket = s3.Bucket(
            self,
            "SC2Replays",
            bucket_name=f"sc2-bot-replays-{self.account}-{env_name}",
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    expiration=Duration.days(365),
                    enabled=True,
                )
            ],
            removal_policy=RemovalPolicy.RETAIN,
        )

        # --- Outputs ---
        CfnOutput(self, "EKSClusterName", value=eks_cluster.cluster_name)
        CfnOutput(self, "DBEndpoint", value=db_instance.db_instance_endpoint_address)
        CfnOutput(self, "ReplayBucket", value=replay_bucket.bucket_name)


# ========================================
# App Entry
# ========================================
app = cdk.App()
SC2BotInfraStack(
    app,
    "SC2BotInfraStack",
    env=cdk.Environment(
        account=os.environ.get("CDK_ACCOUNT", "123456789012"),
        region=os.environ.get("CDK_REGION", "us-east-1"),
    ),
)
app.synth()
