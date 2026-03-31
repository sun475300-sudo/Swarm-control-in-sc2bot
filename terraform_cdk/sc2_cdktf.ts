// SC2 Bot - Terraform CDK (CDKTF) TypeScript Infrastructure
// Stacks: NetworkingStack, ComputeStack, DatabaseStack

import { App, TerraformStack, TerraformOutput, RemoteBackend } from "cdktf";
import { AwsProvider } from "@cdktf/provider-aws/lib/provider";
import { Vpc } from "@cdktf/provider-aws/lib/vpc";
import { Subnet } from "@cdktf/provider-aws/lib/subnet";
import { SecurityGroup } from "@cdktf/provider-aws/lib/security-group";
import { EksCluster } from "@cdktf/provider-aws/lib/eks-cluster";
import { EksNodeGroup } from "@cdktf/provider-aws/lib/eks-node-group";
import { DbInstance } from "@cdktf/provider-aws/lib/db-instance";
import { S3Bucket } from "@cdktf/provider-aws/lib/s3-bucket";
import { EcrRepository } from "@cdktf/provider-aws/lib/ecr-repository";
import { Construct } from "constructs";

// --- Shared Config ---
const SC2_REGION = "us-east-1";
const SC2_ENV    = process.env.ENVIRONMENT ?? "production";

// ============================
// Construct: SC2 Bot Cluster
// ============================
class SC2BotCluster extends Construct {
  public readonly cluster: EksCluster;
  public readonly nodeGroup: EksNodeGroup;

  constructor(scope: Construct, id: string, vpcId: string, subnetIds: string[]) {
    super(scope, id);
    this.cluster = new EksCluster(this, "cluster", {
      name: `sc2-bot-${SC2_ENV}`,
      roleArn: "arn:aws:iam::123456789:role/eks-cluster-role",
      vpcConfig: { subnetIds, endpointPublicAccess: true },
      version: "1.30",
      tags: { Project: "SC2Bot", Env: SC2_ENV },
    });
    this.nodeGroup = new EksNodeGroup(this, "nodegroup", {
      clusterName: this.cluster.name,
      nodeGroupName: "sc2-workers",
      nodeRoleArn: "arn:aws:iam::123456789:role/eks-node-role",
      subnetIds,
      instanceTypes: ["t3.xlarge"],
      scalingConfig: { desiredSize: 3, minSize: 1, maxSize: 10 },
      diskSize: 50,
      labels: { workload: "sc2-bot" },
    });
  }
}

// ============================
// Stack: Networking
// ============================
class NetworkingStack extends TerraformStack {
  public readonly vpc: Vpc;
  public readonly subnetIds: string[];

  constructor(scope: Construct, id: string) {
    super(scope, id);
    new AwsProvider(this, "aws", { region: SC2_REGION });

    this.vpc = new Vpc(this, "vpc", {
      cidrBlock: "10.0.0.0/16",
      enableDnsHostnames: true,
      tags: { Name: "sc2-vpc", Project: "SC2Bot" },
    });

    const subnet = new Subnet(this, "subnet-a", {
      vpcId: this.vpc.id,
      cidrBlock: "10.0.1.0/24",
      availabilityZone: `${SC2_REGION}a`,
      mapPublicIpOnLaunch: true,
    });
    this.subnetIds = [subnet.id];

    new TerraformOutput(this, "vpc-id", { value: this.vpc.id });
  }
}

// ============================
// Stack: Compute (EKS)
// ============================
class ComputeStack extends TerraformStack {
  constructor(scope: Construct, id: string, vpcId: string, subnetIds: string[]) {
    super(scope, id);
    new AwsProvider(this, "aws", { region: SC2_REGION });

    const botCluster = new SC2BotCluster(this, "sc2-cluster", vpcId, subnetIds);

    const ecr = new EcrRepository(this, "ecr", {
      name: "sc2-bot",
      imageScanningConfiguration: { scanOnPush: true },
      imageTagMutability: "IMMUTABLE",
    });

    new TerraformOutput(this, "cluster-name",  { value: botCluster.cluster.name });
    new TerraformOutput(this, "ecr-url",       { value: ecr.repositoryUrl });
  }
}

// ============================
// Stack: Database & Storage
// ============================
class DatabaseStack extends TerraformStack {
  constructor(scope: Construct, id: string) {
    super(scope, id);
    new AwsProvider(this, "aws", { region: SC2_REGION });

    const replayBucket = new S3Bucket(this, "replays", {
      bucket: `sc2-replays-${SC2_ENV}`,
      tags: { Project: "SC2Bot", DataType: "replays" },
    });

    const db = new DbInstance(this, "postgres", {
      identifier:           "sc2-bot-db",
      engine:               "postgres",
      engineVersion:        "16.2",
      instanceClass:        "db.t3.medium",
      allocatedStorage:     100,
      dbName:               "sc2bot",
      username:             "sc2admin",
      password:             process.env.DB_PASSWORD ?? "changeme",
      skipFinalSnapshot:    true,
      multiAz:              SC2_ENV === "production",
      tags:                 { Project: "SC2Bot" },
    });

    new TerraformOutput(this, "replay-bucket", { value: replayBucket.bucket });
    new TerraformOutput(this, "db-endpoint",   { value: db.endpoint });
  }
}

// ============================
// App Entry
// ============================
const app   = new App();
const netw  = new NetworkingStack(app, "sc2-networking");
new ComputeStack(app, "sc2-compute", netw.vpc.id, netw.subnetIds);
new DatabaseStack(app, "sc2-database");
app.synth();
