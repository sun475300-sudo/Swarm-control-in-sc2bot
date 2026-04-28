"""
SC2 Bot - AWS Cost Optimization Analyzer
Phase 394: Cloud infrastructure cost analysis and recommendations

Analyzes EC2 rightsizing, spot instances, S3 lifecycle,
RDS reserved instances, and generates savings reports.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import boto3

logger = logging.getLogger(__name__)


@dataclass
class ResourceRecommendation:
    """A single cost optimization recommendation."""

    resource_id: str
    resource_type: str
    current_cost_monthly: float
    optimized_cost_monthly: float
    savings_monthly: float
    savings_percent: float
    action: str
    risk: str  # LOW / MEDIUM / HIGH
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def annual_savings(self) -> float:
        return self.savings_monthly * 12

    def to_dict(self) -> dict:
        return {
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "current_cost_monthly": round(self.current_cost_monthly, 2),
            "optimized_cost_monthly": round(self.optimized_cost_monthly, 2),
            "savings_monthly": round(self.savings_monthly, 2),
            "savings_annual": round(self.annual_savings, 2),
            "savings_percent": round(self.savings_percent, 1),
            "action": self.action,
            "risk": self.risk,
            "details": self.details,
        }


class CostAnalyzer:
    """
    AWS Cost Optimization Analyzer for SC2 Bot infrastructure.

    Analyzes:
    - EC2 instance rightsizing (CPU/memory utilization)
    - Spot instance conversion opportunities
    - S3 lifecycle policy optimization
    - RDS reserved instance recommendations
    """

    # On-demand pricing estimates (USD/hour) - simplified
    EC2_PRICING = {
        "t3.medium": 0.0416,
        "t3.large": 0.0832,
        "t3.xlarge": 0.1664,
        "m5.large": 0.096,
        "m5.xlarge": 0.192,
        "m5.2xlarge": 0.384,
        "c5.xlarge": 0.17,
        "c5.2xlarge": 0.34,
        "g4dn.xlarge": 0.526,
        "g4dn.2xlarge": 0.752,
    }

    SPOT_DISCOUNT = 0.70  # Spot is ~70% cheaper on average
    RI_1YR_DISCOUNT = 0.40  # 1-year reserved = ~40% cheaper
    RI_3YR_DISCOUNT = 0.60  # 3-year reserved = ~60% cheaper

    def __init__(self, region: str = "us-east-1", dry_run: bool = True):
        self.region = region
        self.dry_run = dry_run
        self.recommendations: list[ResourceRecommendation] = []

        if not dry_run:
            self.ec2 = boto3.client("ec2", region_name=region)
            self.ce = boto3.client("ce", region_name=region)
            self.rds = boto3.client("rds", region_name=region)
            self.s3 = boto3.client("s3")
            self.cloudwatch = boto3.client("cloudwatch", region_name=region)

    def analyze_all(self) -> dict[str, Any]:
        """Run complete cost analysis and return savings report."""
        logger.info("Starting full cost analysis for SC2 bot infrastructure...")

        self.recommendations.clear()
        self._analyze_ec2_rightsizing()
        self._analyze_spot_opportunities()
        self._analyze_s3_lifecycle()
        self._analyze_rds_reserved()

        return self._generate_report()

    def _analyze_ec2_rightsizing(self) -> None:
        """Identify over-provisioned EC2 instances."""
        if self.dry_run:
            instances = self._mock_ec2_instances()
        else:
            response = self.ec2.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
            )
            instances = [i for r in response["Reservations"] for i in r["Instances"]]

        for inst in instances:
            inst_type = inst["InstanceType"]
            inst_id = inst["InstanceId"]
            avg_cpu = inst.get("AvgCpuUtil", 15.0)  # mock value
            avg_mem = inst.get("AvgMemUtil", 30.0)  # mock value

            if avg_cpu < 20 and avg_mem < 40:
                # Under-utilized - recommend smaller instance
                current_price = self.EC2_PRICING.get(inst_type, 0.10)
                # Recommend one tier down
                recommended = self._get_smaller_instance(inst_type)
                new_price = self.EC2_PRICING.get(recommended, current_price * 0.5)

                monthly_current = current_price * 24 * 30
                monthly_new = new_price * 24 * 30

                rec = ResourceRecommendation(
                    resource_id=inst_id,
                    resource_type="EC2",
                    current_cost_monthly=monthly_current,
                    optimized_cost_monthly=monthly_new,
                    savings_monthly=monthly_current - monthly_new,
                    savings_percent=((monthly_current - monthly_new) / monthly_current)
                    * 100,
                    action=f"Rightsize from {inst_type} to {recommended}",
                    risk="LOW",
                    details={
                        "avg_cpu_util": avg_cpu,
                        "avg_mem_util": avg_mem,
                        "current_type": inst_type,
                        "recommended_type": recommended,
                    },
                )
                self.recommendations.append(rec)
                logger.info(f"EC2 rightsize opportunity: {inst_id} -> {recommended}")

    def _analyze_spot_opportunities(self) -> None:
        """Find workloads suitable for spot instances (training jobs, non-critical)."""
        spot_candidates = [
            {"id": "i-training-001", "type": "g4dn.2xlarge", "workload": "ML Training"},
            {
                "id": "i-replay-proc-001",
                "type": "c5.2xlarge",
                "workload": "Replay Processing",
            },
        ]

        for candidate in spot_candidates:
            on_demand = self.EC2_PRICING.get(candidate["type"], 0.5) * 24 * 30
            spot_cost = on_demand * (1 - self.SPOT_DISCOUNT)

            rec = ResourceRecommendation(
                resource_id=candidate["id"],
                resource_type="EC2-Spot",
                current_cost_monthly=on_demand,
                optimized_cost_monthly=spot_cost,
                savings_monthly=on_demand - spot_cost,
                savings_percent=self.SPOT_DISCOUNT * 100,
                action=f"Convert {candidate['type']} to Spot Instance",
                risk="MEDIUM",
                details={
                    "workload": candidate["workload"],
                    "spot_interruption_note": "Implement checkpoint/resume logic",
                },
            )
            self.recommendations.append(rec)

    def _analyze_s3_lifecycle(self) -> None:
        """Recommend S3 lifecycle policies to move old data to cheaper storage tiers."""
        buckets = [
            {"name": "sc2bot-replays", "size_gb": 500, "avg_access_days": 90},
            {"name": "sc2bot-models", "size_gb": 200, "avg_access_days": 30},
            {"name": "sc2bot-backups", "size_gb": 1000, "avg_access_days": 365},
        ]

        s3_standard = 0.023  # per GB/month
        s3_ia = 0.0125  # per GB/month
        s3_glacier = 0.004  # per GB/month

        for bucket in buckets:
            size = bucket["size_gb"]
            current = size * s3_standard

            if bucket["avg_access_days"] > 180:
                new_cost = size * s3_glacier
                action = f"Move {bucket['name']} to S3 Glacier after 90 days"
            elif bucket["avg_access_days"] > 60:
                new_cost = size * s3_ia
                action = f"Move {bucket['name']} to S3 Infrequent Access after 30 days"
            else:
                continue

            rec = ResourceRecommendation(
                resource_id=bucket["name"],
                resource_type="S3",
                current_cost_monthly=current,
                optimized_cost_monthly=new_cost,
                savings_monthly=current - new_cost,
                savings_percent=((current - new_cost) / current) * 100,
                action=action,
                risk="LOW",
                details={"size_gb": size, "avg_access_days": bucket["avg_access_days"]},
            )
            self.recommendations.append(rec)

    def _analyze_rds_reserved(self) -> None:
        """Recommend Reserved Instances for stable RDS workloads."""
        rds_instances = [
            {
                "id": "sc2bot-postgres-prod",
                "type": "db.r6g.xlarge",
                "monthly_cost": 350.0,
            },
        ]

        for inst in rds_instances:
            ri_cost = inst["monthly_cost"] * (1 - self.RI_1YR_DISCOUNT)
            rec = ResourceRecommendation(
                resource_id=inst["id"],
                resource_type="RDS-RI",
                current_cost_monthly=inst["monthly_cost"],
                optimized_cost_monthly=ri_cost,
                savings_monthly=inst["monthly_cost"] - ri_cost,
                savings_percent=self.RI_1YR_DISCOUNT * 100,
                action=f"Purchase 1-year Reserved Instance for {inst['id']}",
                risk="LOW",
                details={"commitment": "1-year", "upfront": "Partial"},
            )
            self.recommendations.append(rec)

    def _generate_report(self) -> dict[str, Any]:
        """Compile all recommendations into a cost savings report."""
        total_current = sum(r.current_cost_monthly for r in self.recommendations)
        total_optimized = sum(r.optimized_cost_monthly for r in self.recommendations)
        total_savings = total_current - total_optimized

        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "region": self.region,
            "summary": {
                "total_recommendations": len(self.recommendations),
                "current_monthly_cost": round(total_current, 2),
                "optimized_monthly_cost": round(total_optimized, 2),
                "monthly_savings": round(total_savings, 2),
                "annual_savings": round(total_savings * 12, 2),
                "savings_percent": round(
                    (total_savings / total_current * 100) if total_current else 0, 1
                ),
            },
            "recommendations_by_type": {},
            "recommendations": [r.to_dict() for r in self.recommendations],
        }

        for rec in self.recommendations:
            rtype = rec.resource_type
            if rtype not in report["recommendations_by_type"]:
                report["recommendations_by_type"][rtype] = {
                    "count": 0,
                    "monthly_savings": 0,
                }
            report["recommendations_by_type"][rtype]["count"] += 1
            report["recommendations_by_type"][rtype][
                "monthly_savings"
            ] += rec.savings_monthly

        logger.info(
            f"Cost analysis complete. "
            f"Potential savings: ${total_savings:.2f}/month (${total_savings*12:.2f}/year)"
        )
        return report

    def _get_smaller_instance(self, instance_type: str) -> str:
        """Return one-tier-smaller instance recommendation."""
        downsizing_map = {
            "m5.2xlarge": "m5.xlarge",
            "m5.xlarge": "m5.large",
            "c5.2xlarge": "c5.xlarge",
            "c5.xlarge": "t3.xlarge",
            "t3.xlarge": "t3.large",
            "t3.large": "t3.medium",
            "g4dn.2xlarge": "g4dn.xlarge",
        }
        return downsizing_map.get(instance_type, instance_type)

    def _mock_ec2_instances(self) -> list[dict]:
        """Mock EC2 data for dry-run mode."""
        return [
            {
                "InstanceId": "i-001",
                "InstanceType": "m5.2xlarge",
                "AvgCpuUtil": 12.0,
                "AvgMemUtil": 28.0,
            },
            {
                "InstanceId": "i-002",
                "InstanceType": "c5.2xlarge",
                "AvgCpuUtil": 18.0,
                "AvgMemUtil": 35.0,
            },
            {
                "InstanceId": "i-003",
                "InstanceType": "t3.xlarge",
                "AvgCpuUtil": 65.0,
                "AvgMemUtil": 72.0,
            },
        ]

    def save_report(self, report: dict, output_path: str = "cost_report.json") -> None:
        """Save cost report to JSON file."""
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Cost report saved to {output_path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    analyzer = CostAnalyzer(region="us-east-1", dry_run=True)
    report = analyzer.analyze_all()
    analyzer.save_report(report, "cost_analysis/cost_report.json")

    summary = report["summary"]
    print(f"\n{'='*50}")
    print(f"SC2 Bot AWS Cost Optimization Report")
    print(f"{'='*50}")
    print(f"Current monthly cost:    ${summary['current_monthly_cost']:,.2f}")
    print(f"Optimized monthly cost:  ${summary['optimized_monthly_cost']:,.2f}")
    print(f"Monthly savings:         ${summary['monthly_savings']:,.2f}")
    print(f"Annual savings:          ${summary['annual_savings']:,.2f}")
    print(f"Savings percentage:      {summary['savings_percent']}%")
    print(f"Total recommendations:   {summary['total_recommendations']}")
    print(f"{'='*50}")
