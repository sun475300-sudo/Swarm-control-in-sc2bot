# SC2 Bot Infrastructure - Disaster Recovery Runbook

**Version:** 1.0
**Last Updated:** 2026-03-31
**Owner:** SC2 Bot DevOps Team
**Classification:** Internal

---

## 1. RTO / RPO Targets

| Tier | Service | RTO (Recovery Time) | RPO (Recovery Point) |
|------|---------|--------------------|--------------------|
| P0 | SC2 Bot Core | 15 minutes | 5 minutes |
| P1 | PostgreSQL Database | 30 minutes | 1 hour |
| P1 | Model Checkpoints | 1 hour | 4 hours |
| P2 | Redis Cache | 5 minutes (stateless rebuild) | N/A |
| P2 | Monitoring Stack | 2 hours | 24 hours |
| P3 | Replay Storage | 4 hours | 24 hours |

---

## 2. Database Backup & Restore

### 2.1 Automated Backup Schedule

```bash
# Runs via CronJob in Kubernetes - every 1 hour
kubectl get cronjob postgres-backup -n sc2bot

# Manual backup trigger
kubectl create job --from=cronjob/postgres-backup manual-backup-$(date +%Y%m%d%H%M) -n sc2bot
```

### 2.2 Restore from S3 Backup

```bash
# Step 1: List available backups
aws s3 ls s3://sc2bot-backups/postgres/ --recursive | sort | tail -20

# Step 2: Download latest backup
BACKUP_FILE=$(aws s3 ls s3://sc2bot-backups/postgres/ | sort | tail -1 | awk '{print $4}')
aws s3 cp s3://sc2bot-backups/postgres/$BACKUP_FILE /tmp/sc2bot_restore.sql.gz

# Step 3: Restore to new postgres instance
gunzip /tmp/sc2bot_restore.sql.gz
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U sc2bot -d sc2bot < /tmp/sc2bot_restore.sql

# Step 4: Verify row counts
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U sc2bot -d sc2bot -c "
  SELECT schemaname, relname, n_live_tup
  FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 10;"
```

### 2.3 Point-in-Time Recovery (PITR)

```bash
# Restore to specific timestamp using WAL logs
pg_restore --target-time="2026-03-31 10:00:00+00" \
  --recovery-target-action=promote \
  -d sc2bot /tmp/base_backup
```

---

## 3. Model Checkpoint Recovery

### 3.1 Checkpoint Backup Location

- **Primary:** `s3://sc2bot-models/checkpoints/`
- **Secondary:** `gs://sc2bot-models-backup/checkpoints/`
- **Local cache:** `/checkpoints/` (PVC - EFS)

### 3.2 Restore Latest Checkpoint

```bash
# List available checkpoints
aws s3 ls s3://sc2bot-models/checkpoints/ | sort | tail -10

# Restore latest model checkpoint
LATEST=$(aws s3 ls s3://sc2bot-models/checkpoints/ | sort | tail -1 | awk '{print $4}')
aws s3 cp s3://sc2bot-models/checkpoints/$LATEST /checkpoints/ppo_model_restored.pt

# Verify checkpoint integrity
python -c "
import torch
ckpt = torch.load('/checkpoints/ppo_model_restored.pt')
print(f'Epoch: {ckpt[\"epoch\"]}, Win rate: {ckpt[\"metrics\"][\"win_rate\"]:.2%}')
"
```

### 3.3 Fallback to Rule-Based Bot

If model recovery takes >1 hour, activate the fallback:

```bash
kubectl set env deployment/sc2bot USE_RULE_BASED_FALLBACK=true -n sc2bot
kubectl rollout status deployment/sc2bot -n sc2bot
```

---

## 4. Full Cluster Rebuild

### 4.1 Prerequisites

```bash
# Tools required
aws --version          # AWS CLI 2.x
kubectl version        # 1.28+
helm version           # 3.12+
terraform --version    # 1.5+
```

### 4.2 Step-by-Step Cluster Rebuild

```bash
# Step 1: Recreate EKS cluster from Terraform
cd terraform/
terraform init
terraform plan -var-file=production.tfvars
terraform apply -var-file=production.tfvars -auto-approve

# Step 2: Update kubeconfig
aws eks update-kubeconfig --region us-east-1 --name sc2bot-prod

# Step 3: Install core add-ons via Helm
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm install sealed-secrets sealed-secrets/sealed-secrets -n kube-system

helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/
helm install metrics-server metrics-server/metrics-server -n kube-system

# Step 4: Apply all manifests
kubectl apply -f k8s_manifests/sc2bot-full.yaml

# Step 5: Restore data (see sections 2 and 3)

# Step 6: Verify all pods healthy
kubectl get pods -n sc2bot
kubectl get svc -n sc2bot
```

---

## 5. Data Loss Scenarios

| Scenario | Impact | Recovery Action | Time |
|----------|--------|----------------|------|
| Redis failure | Cache miss surge | Restart pod, cache warms automatically | 5 min |
| Single DB replica failure | Read performance degradation | Promote standby replica | 10 min |
| Primary DB loss | Service degradation | Restore from backup (see §2) | 30 min |
| EFS volume corruption | Checkpoints unavailable | Restore from S3 (see §3) | 60 min |
| Full cluster loss | Complete outage | Full rebuild (see §4) | 4 hours |
| S3 bucket deletion | Permanent data loss | Restore from cross-region replica | 6 hours |

---

## 6. Contact Tree

| Role | Name | Primary Contact | Secondary Contact |
|------|------|-----------------|-------------------|
| On-call Engineer | Rotation | PagerDuty: sc2bot-oncall | Slack: #sc2bot-alerts |
| Platform Lead | Platform Team | platform@sc2bot.internal | +82-10-XXXX-XXXX |
| Database Admin | DBA Team | dba@sc2bot.internal | Slack: #dba-oncall |
| ML Engineering | ML Team | ml@sc2bot.internal | Slack: #ml-ops |
| Management Escalation | Project Lead | lead@sc2bot.internal | Emergency: +82-10-XXXX-YYYY |

### 6.1 Escalation Timeline

- **0-15 min:** On-call engineer responds and triages
- **15-30 min:** Team lead notified if P0/P1 unresolved
- **30-60 min:** Management escalation if service still down
- **60+ min:** Executive notification and external vendor support

---

## 7. Post-Incident Review

After every P0/P1 incident, complete within 48 hours:

1. **Timeline reconstruction** - What happened, when, who acted
2. **Root cause analysis** - 5-whys methodology
3. **Impact assessment** - Users affected, games disrupted, data lost
4. **Action items** - Preventive measures with owners and deadlines
5. **Runbook updates** - Update this document if gaps found

*Template:* `runbooks/incident_template.md`
