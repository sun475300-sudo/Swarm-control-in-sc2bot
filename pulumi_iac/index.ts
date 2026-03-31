import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as awsx from "@pulumi/awsx";
import * as eks from "@pulumi/eks";
import * as gcp from "@pulumi/gcp";
import * as k8s from "@pulumi/kubernetes";

// ─── Configuration ────────────────────────────────────────────────────────────
const config = new pulumi.Config();
const projectName = config.get("projectName") || "sc2bot";
const environment = config.get("environment") || "prod";
const awsRegion = config.get("awsRegion") || "us-east-1";
const gcpProject = config.require("gcpProject");
const gcpRegion = config.get("gcpRegion") || "us-central1";
const dbPassword = config.requireSecret("dbPassword");
const nodeCount = config.getNumber("nodeCount") || 3;
const nodeInstanceType = config.get("nodeInstanceType") || "t3.xlarge";

const tags: Record<string, string> = {
    Project: projectName,
    Environment: environment,
    ManagedBy: "pulumi",
};

// ─── AWS VPC ──────────────────────────────────────────────────────────────────
const vpc = new awsx.ec2.Vpc(`${projectName}-vpc`, {
    cidrBlock: "10.0.0.0/16",
    numberOfAvailabilityZones: 3,
    subnetStrategy: awsx.ec2.SubnetAllocationStrategy.Auto,
    tags,
});

// ─── AWS ECR Registry ─────────────────────────────────────────────────────────
const ecrRepo = new aws.ecr.Repository(`${projectName}-ecr`, {
    name: `${projectName}/zerg-ai`,
    imageTagMutability: "MUTABLE",
    imageScanningConfiguration: {
        scanOnPush: true,
    },
    encryptionConfigurations: [
        { encryptionType: "AES256" },
    ],
    tags,
});

const ecrLifecyclePolicy = new aws.ecr.LifecyclePolicy(`${projectName}-ecr-lifecycle`, {
    repository: ecrRepo.name,
    policy: JSON.stringify({
        rules: [
            {
                rulePriority: 1,
                description: "Keep last 10 production images",
                selection: {
                    tagStatus: "tagged",
                    tagPrefixList: ["prod-"],
                    countType: "imageCountMoreThan",
                    countNumber: 10,
                },
                action: { type: "expire" },
            },
            {
                rulePriority: 2,
                description: "Expire untagged images after 14 days",
                selection: {
                    tagStatus: "untagged",
                    countType: "sinceImagePushed",
                    countUnit: "days",
                    countNumber: 14,
                },
                action: { type: "expire" },
            },
        ],
    }),
});

// ─── AWS EKS Cluster ──────────────────────────────────────────────────────────
const eksCluster = new eks.Cluster(`${projectName}-eks`, {
    vpcId: vpc.vpcId,
    privateSubnetIds: vpc.privateSubnetIds,
    publicSubnetIds: vpc.publicSubnetIds,
    instanceType: nodeInstanceType,
    desiredCapacity: nodeCount,
    minSize: 1,
    maxSize: nodeCount * 2,
    enabledClusterLogTypes: [
        "api", "audit", "authenticator", "controllerManager", "scheduler",
    ],
    tags,
});

// ─── AWS S3 Replay Storage ────────────────────────────────────────────────────
const replayBucket = new aws.s3.Bucket(`${projectName}-replays`, {
    bucket: `${projectName}-replays-${environment}`,
    acl: "private",
    serverSideEncryptionConfiguration: {
        rule: {
            applyServerSideEncryptionByDefault: {
                sseAlgorithm: "aws:kms",
            },
        },
    },
    versioningConfiguration: { status: "Enabled" },
    lifecycleRules: [
        {
            id: "archive-replays",
            enabled: true,
            transitions: [
                { days: 30, storageClass: "STANDARD_IA" },
                { days: 90, storageClass: "GLACIER" },
            ],
        },
    ],
    tags,
});

const bucketPublicAccessBlock = new aws.s3.BucketPublicAccessBlock(`${projectName}-replays-pab`, {
    bucket: replayBucket.id,
    blockPublicAcls: true,
    blockPublicPolicy: true,
    ignorePublicAcls: true,
    restrictPublicBuckets: true,
});

// ─── AWS RDS PostgreSQL ───────────────────────────────────────────────────────
const dbSubnetGroup = new aws.rds.SubnetGroup(`${projectName}-db-subnet`, {
    subnetIds: vpc.privateSubnetIds,
    tags,
});

const dbSecurityGroup = new aws.ec2.SecurityGroup(`${projectName}-db-sg`, {
    vpcId: vpc.vpcId,
    ingress: [
        {
            protocol: "tcp",
            fromPort: 5432,
            toPort: 5432,
            cidrBlocks: ["10.0.0.0/16"],
            description: "PostgreSQL from VPC",
        },
    ],
    egress: [
        { protocol: "-1", fromPort: 0, toPort: 0, cidrBlocks: ["0.0.0.0/0"] },
    ],
    tags,
});

const replayDb = new aws.rds.Instance(`${projectName}-rds`, {
    identifier: `${projectName}-replays-db`,
    engine: "postgres",
    engineVersion: "15.4",
    instanceClass: "db.t3.medium",
    allocatedStorage: 100,
    storageType: "gp3",
    storageEncrypted: true,
    dbName: "sc2bot_replays",
    username: "sc2bot_admin",
    password: dbPassword,
    dbSubnetGroupName: dbSubnetGroup.name,
    vpcSecurityGroupIds: [dbSecurityGroup.id],
    multiAz: false,
    publiclyAccessible: false,
    deletionProtection: true,
    backupRetentionPeriod: 7,
    performanceInsightsEnabled: true,
    tags,
});

// ─── GCP GKE Cluster (multi-cloud fallback) ───────────────────────────────────
const gcpNetwork = new gcp.compute.Network(`${projectName}-gcp-vpc`, {
    project: gcpProject,
    autoCreateSubnetworks: false,
});

const gcpSubnet = new gcp.compute.Subnetwork(`${projectName}-gcp-subnet`, {
    project: gcpProject,
    region: gcpRegion,
    network: gcpNetwork.id,
    ipCidrRange: "10.1.0.0/16",
    secondaryIpRanges: [
        { rangeName: "pods", ipCidrRange: "10.2.0.0/16" },
        { rangeName: "services", ipCidrRange: "10.3.0.0/16" },
    ],
});

const gkeCluster = new gcp.container.Cluster(`${projectName}-gke`, {
    project: gcpProject,
    location: gcpRegion,
    initialNodeCount: 1,
    removeDefaultNodePool: true,
    network: gcpNetwork.selfLink,
    subnetwork: gcpSubnet.selfLink,
    ipAllocationPolicy: {
        clusterSecondaryRangeName: "pods",
        servicesSecondaryRangeName: "services",
    },
    loggingService: "logging.googleapis.com/kubernetes",
    monitoringService: "monitoring.googleapis.com/kubernetes",
});

// ─── Exports ──────────────────────────────────────────────────────────────────
export const clusterName = eksCluster.eksCluster.name;
export const clusterKubeconfig = eksCluster.kubeconfig;
export const dbEndpoint = replayDb.endpoint;
export const dbPort = replayDb.port;
export const replayBucketName = replayBucket.bucket;
export const replayBucketArn = replayBucket.arn;
export const registryUrl = ecrRepo.repositoryUrl;
export const gkeClusterName = gkeCluster.name;
export const vpcId = vpc.vpcId;
