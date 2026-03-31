# SC2 Bot — Monitoring & Incident Response Runbook

**Version**: 1.0 | **Last Updated**: 2026-03-31 | **Owner**: SC2 Bot Platform Team

---

## 1. Service Health Checks

### 1.1 Quick Health Status

```bash
# API service health
curl -s http://sc2bot-api:8000/health | jq .

# Kubernetes pod status
kubectl get pods -n sc2bot -o wide

# Check deployment rollout
kubectl rollout status deployment/sc2bot -n sc2bot

# Recent pod logs
kubectl logs -n sc2bot -l app=sc2bot --tail=100
```

### 1.2 Key Metrics to Monitor

| Metric | Dashboard | Healthy Threshold | Alert Threshold |
|--------|-----------|-------------------|-----------------|
| API p99 latency | Grafana > SC2Bot API | < 200 ms | > 500 ms |
| Inference throughput | Grafana > ML Metrics | > 100 req/s | < 50 req/s |
| Win rate (7d avg) | Grafana > Game Stats | > 55% | < 40% |
| GPU utilization | Grafana > Infrastructure | 60–90% | < 20% or > 95% |
| Model memory (VRAM) | Grafana > Infrastructure | < 80% | > 90% |
| Error rate (5xx) | Grafana > SC2Bot API | < 0.1% | > 1% |
| Queue depth | Grafana > SC2Bot API | < 50 | > 200 |

### 1.3 Prometheus Queries

```promql
# API error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# p99 inference latency
histogram_quantile(0.99, rate(inference_duration_seconds_bucket[5m]))

# Games per hour
rate(games_completed_total[1h]) * 3600

# Active game sessions
sc2bot_active_sessions
```

---

## 2. Common Alerts & Resolution Steps

### Alert: `SC2BotHighLatency`
**Condition**: p99 API latency > 500ms for 5 minutes

**Resolution Steps**:
1. Check current pod resource usage: `kubectl top pods -n sc2bot`
2. Check for traffic spike: Grafana > SC2Bot API > Request Rate
3. If GPU-bound: restart inference workers — `kubectl rollout restart deployment/sc2bot-inference -n sc2bot`
4. If CPU-bound: scale horizontally — `kubectl scale deployment/sc2bot-api --replicas=6 -n sc2bot`
5. Check for model regression: compare current p99 to 24h baseline in Grafana

---

### Alert: `SC2BotLowWinRate`
**Condition**: 6-hour win rate drops below 40%

**Resolution Steps**:
1. Check opponent list for new/stronger bots: `kubectl logs -n sc2bot -l app=sc2bot-ladder`
2. Compare current model version vs. last deployed: `kubectl get deployment sc2bot -n sc2bot -o yaml | grep image`
3. Review recent match replays via replay analyzer API: `GET /api/replays?result=loss&limit=20`
4. If model regression: roll back to previous version (see Section 4)
5. Notify ML team if win rate < 35% for > 2 hours

---

### Alert: `SC2BotPodCrashLooping`
**Condition**: Pod restart count > 5 in 15 minutes

**Resolution Steps**:
1. Get crash reason: `kubectl describe pod <pod-name> -n sc2bot`
2. Fetch last crash logs: `kubectl logs <pod-name> -n sc2bot --previous`
3. Common causes:
   - OOMKilled: increase memory limits in `helm_charts/sc2bot/values.yaml`
   - Config error: verify ConfigMap — `kubectl get configmap sc2bot-config -n sc2bot -o yaml`
   - Dependency failure: check DB/Redis connectivity
4. If systemic: scale down and investigate — `kubectl scale deployment/sc2bot --replicas=0 -n sc2bot`

---

### Alert: `SC2BotQueueSaturation`
**Condition**: Action request queue depth > 200 for 3 minutes

**Resolution Steps**:
1. Immediately scale up API replicas: `kubectl scale deployment/sc2bot-api --replicas=10 -n sc2bot`
2. Check if inference workers are healthy: `kubectl get pods -n sc2bot -l role=inference`
3. Enable request shedding if needed (circuit breaker): `kubectl set env deployment/sc2bot SHED_LOAD=true -n sc2bot`
4. Alert on-call if queue does not clear within 10 minutes

---

## 3. Escalation Paths

| Severity | Response Time | Primary On-Call | Escalation |
|----------|---------------|-----------------|------------|
| P0 — Service Down | 5 min | Platform Engineer | ML Lead + CTO |
| P1 — Degraded | 15 min | Platform Engineer | ML Lead |
| P2 — Minor | 1 hour | Assigned Engineer | Team Lead |
| P3 — Informational | Next business day | — | — |

**PagerDuty**: `#sc2bot-alerts` Slack channel auto-pages on-call for P0/P1.

---

## 4. Rollback Procedures

### 4.1 Helm Rollback (Recommended)

```bash
# View rollout history
helm history sc2bot -n sc2bot

# Rollback to previous release
helm rollback sc2bot -n sc2bot

# Rollback to specific revision
helm rollback sc2bot 3 -n sc2bot

# Verify rollback
kubectl rollout status deployment/sc2bot -n sc2bot
```

### 4.2 Image Rollback (Quick)

```bash
# Get previous image tag from deployment history
kubectl rollout history deployment/sc2bot -n sc2bot --revision=2

# Roll back one revision
kubectl rollout undo deployment/sc2bot -n sc2bot

# Verify pods are healthy
kubectl get pods -n sc2bot -l app=sc2bot
```

### 4.3 Model Weight Rollback

```bash
# List available model versions in MLflow
python -c "import mlflow; client = mlflow.tracking.MlflowClient(); [print(mv) for mv in client.search_model_versions('name=\"sc2bot\"')]"

# Trigger hot-reload with specific version
curl -X POST http://sc2bot-api:8000/api/admin/reload-model \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -d '{"model_version": "v1.2.3"}'
```

---

## 5. Performance Tuning

### 5.1 Inference Latency Too High
- Increase batch size (if throughput > latency is acceptable): set `INFERENCE_BATCH_SIZE=32`
- Enable TensorRT optimization: set `USE_TENSORRT=true` and rebuild image
- Reduce model size: switch from `sc2bot-large` to `sc2bot-small` in values.yaml
- Pin inference pods to GPU nodes: add `nodeSelector: gpu: "true"` to deployment

### 5.2 Memory Pressure
- Enable gradient checkpointing during training: `GRADIENT_CHECKPOINT=true`
- Reduce replay buffer size: `REPLAY_BUFFER_SIZE=50000` (from 200000)
- Enable mixed-precision: `USE_AMP=true`

### 5.3 Win Rate Plateau
- Increase entropy coefficient: `ENTROPY_COEF=0.02` (from 0.01)
- Adjust curriculum difficulty: lower `CURRICULUM_WIN_THRESHOLD=0.65` (from 0.75)
- Enable self-play: `SELF_PLAY_RATIO=0.3`
- Review reward shaping weights in `reward_shaper/shaper.py`
