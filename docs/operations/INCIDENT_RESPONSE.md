# Incident Response Guide
## LuminaMind Deep Agent Framework

> **Purpose**: Standardized incident response procedures  
> **Last Updated**: November 26, 2025  
> **Emergency Hotline**: +1-XXX-XXX-XXXX

---

## Quick Reference

### Severity Levels

| Level | Description | Response Time | Example |
|-------|-------------|---------------|---------|
| **P0** | Critical outage | 15 min | Complete service down |
| **P1** | Major incident | 1 hour | High error rate, data loss |
| **P2** | Minor incident | 4 hours | Degraded performance |
| **P3** | Low impact | 1 business day | Non-critical bug |

### Emergency Contacts

| Role | Contact | Availability |
|------|---------|--------------|
| Incident Commander | eng-lead@company.com | 24/7 |
| On-Call Engineer | oncall@company.com | 24/7 |
| Security Team | security@company.com | 24/7 |
| DevOps Lead | devops@company.com | Business hours |
| Product Manager | pm@company.com | Business hours |

### Communication Channels

- **Incident Bridge**: Zoom link (pinned in #incidents)
- **Slack**: #incident-response
- **Status Page**: https://status.yourcompany.com
- **Escalation**: PagerDuty

---

## 1. Incident Response Process

### Phase 1: Detection & Alert (0-5 minutes)

#### Automated Detection
```bash
# Alerts trigger via:
# 1. Prometheus → Alertmanager → PagerDuty/Slack
# 2. User reports → Slack #support
# 3. Monitoring dashboards → Manual detection
```

#### Initial Response (On-Call)
1. **Acknowledge** the alert in PagerDuty (stops escalation)
2. **Assess severity** using the table above
3. **Create incident** in Slack:
   ```bash
   /incident create P1 "High error rate on production"
   ```
4. **Join incident channel**: `#incident-YYYY-MM-DD-NNN`

### Phase 2: Triage (5-15 minutes)

#### Quick Health Check
```bash
# 1. Check if service is up
kubectl get pods -l app=luminamind

# 2. Check error rate
curl 'http://prometheus:9090/api/v1/query?query=rate(luminamind_requests_total{status=~"5.."}[5m])'

# 3. Check logs for errors
kubectl logs -l app=luminamind --tail=100 | grep ERROR

# 4. Check recent deployments
kubectl rollout history deployment/luminamind
```

#### Severity Assessment

**Upgrade to P0** if:
- [ ] Service completely down (all pods crashed)
- [ ] Data loss occurring
- [ ] Security breach detected
- [ ] Affecting >50% of users

**Upgrade to P1** if:
- [ ] Error rate >5%
- [ ] P95 latency >20s
- [ ] Core functionality broken
- [ ] Affecting >10% of users

#### Escalation Decision Tree
```
Is service completely down?
├─ YES → P0: Page Incident Commander immediately
└─ NO
    └─ Is error rate >5% or affecting multiple users?
        ├─ YES → P1: Page on-call + notify #incident-response
        └─ NO → P2: Handle during business hours
```

### Phase 3: Investigation (15 min - 2 hours)

#### Gather Evidence

1. **Export logs** (last 1 hour):
   ```bash
   kubectl logs -l app=luminamind --since=1h > /tmp/incident-logs.txt
   
   # Upload to incident channel
   slack-cli upload /tmp/incident-logs.txt -c "#incident-YYYY-MM-DD-NNN"
   ```

2. **Snapshot metrics**:
   ```bash
   # Error rate
   curl 'http://prometheus:9090/api/v1/query_range?query=rate(luminamind_requests_total{status=~"5.."}[5m])&start=...' > metrics.json
   
   # CPU/Memory
   kubectl top pods -l app=luminamind > resource-usage.txt
   ```

3. **Check recent changes**:
   ```bash
   # Recent deployments
   kubectl rollout history deployment/luminamind --revision=5
   
   # Git commits
   git log --since="2 hours ago" --oneline
   ```

4. **Review distributed traces** in Jaeger:
   - Go to http://jaeger:16686
   - Search for failed requests
   - Identify where latency/errors originate

#### Common Incident Types & Diagnosis

**Type 1: High Error Rate**
```bash
# Find which endpoint is failing
kubectl logs -l app=luminamind --tail=1000 | grep -E "ERROR|CRITICAL" | cut -d' ' -f5-10 | sort | uniq -c | sort -rn

# Check if LLM API is down
curl -X POST https://api.z.ai/api/paas/v4/chat/completions \
  -H "Authorization: Bearer $GLM_API_KEY" \
  -d '{"model": "glm-4.5-flash", "messages": [{"role": "user", "content": "test"}]}'

# Check Redis connectivity
kubectl exec deployment/luminamind -- redis-cli -h redis PING
```

**Type 2: High Latency**
```bash
# Identify slow tools
curl 'http://prometheus:9090/api/v1/query?query=topk(5,avg(rate(luminamind_tool_duration_seconds_sum[5m]))by(tool_name))'

# Check cache hit rate
curl 'http://prometheus:9090/api/v1/query?query=sum(rate(luminamind_cache_operations_total{result="hit"}[5m]))/sum(rate(luminamind_cache_operations_total{operation="get"}[5m]))'

# Check if Redis is slow
kubectl exec redis-0 -- redis-cli INFO stats | grep instantaneous_ops_per_sec
```

**Type 3: Pod Crashes**
```bash
# Get crash details
kubectl describe pod luminamind-XXX

# Check events
kubectl get events --sort-by='.lastTimestamp' | grep luminamind

# Review previous logs (from crashed pod)
kubectl logs luminamind-XXX --previous
```

**Type 4: Resource Exhaustion**
```bash
# Check resource usage
kubectl top nodes
kubectl top pods -l app=luminamind

# Check if hitting limits
kubectl describe pod luminamind-XXX | grep -A5 Limits

# Check disk usage (if applicable)
kubectl exec deployment/luminamind -- df -h
```

### Phase 4: Mitigation (15 min - 4 hours)

#### Immediate Actions (Choose based on diagnosis)

**Option 1: Rollback Recent Deployment**
```bash
# View rollout history
kubectl rollout history deployment/luminamind

# Rollback to previous version
kubectl rollout undo deployment/luminamind

# Verify rollback
kubectl rollout status deployment/luminamind

# Monitor error rate
watch 'curl -s http://prometheus:9090/api/v1/query?query=rate(luminamind_requests_total{status=~"5.."}[1m])'
```

**Option 2: Scale Up (if resource exhaustion)**
```bash
# Increase replicas
kubectl scale deployment luminamind --replicas=6

# Or increase resource limits
kubectl set resources deployment luminamind -c=luminamind --limits=memory=4Gi,cpu=4000m
```

**Option 3: Restart Pods (if transient issue)**
```bash
# Rolling restart
kubectl rollout restart deployment/luminamind

# Or delete specific unhealthy pods
kubectl delete pod luminamind-UNHEALTHY-POD
```

**Option 4: Enable Maintenance Mode**
```bash
# Return HTTP 503 to trigger client retries
kubectl patch deployment luminamind -p '{"spec":{"replicas":0}}'

# Deploy minimal service with error page
kubectl apply -f k8s/maintenance-mode.yaml
```

**Option 5: Failover to Backup Region** (if multi-region)
```bash
# Update DNS to point to backup region
# (Requires pre-configured multi-region deployment)
```

**Option 6: Disable Problematic Feature**
```bash
# Via environment variable
kubectl set env deployment/luminamind DISABLE_WEB_SEARCH=true

# Or via config map
kubectl edit configmap luminamind-config
# Set: enable_web_search: false
```

#### Communication During Mitigation

**Update status page** (every 30 minutes):
```bash
# Post update
curl -X POST https://api.statuspage.io/v1/pages/YOUR_PAGE_ID/incidents/INCIDENT_ID \
  -H "Authorization: OAuth YOUR_TOKEN" \
  -d "incident[status]=investigating&incident[message]=We are investigating the issue..."
```

**Update incident channel**:
```
/incident update "Rolled back to v1.2.3. Monitoring error rate. ETA for resolution: 30 minutes."
```

### Phase 5: Recovery (1-4 hours)

#### Verification Checklist

- [ ] **Error rate** back to normal (<0.5%)
  ```bash
  curl 'http://prometheus:9090/api/v1/query?query=rate(luminamind_requests_total{status=~"5.."}[5m])'
  ```

- [ ] **Latency** within SLA (P95 <5s)
  ```bash
  curl 'http://prometheus:9090/api/v1/query?query=histogram_quantile(0.95,luminamind_request_duration_seconds_bucket)'
  ```

- [ ] **All pods** healthy
  ```bash
  kubectl get pods -l app=luminamind
  # All should be Running with READY 1/1
  ```

- [ ] **No new alerts** firing
  ```bash
  curl http://prometheus:9090/api/v1/alerts | jq '.data.alerts[] | select(.state=="firing")'
  ```

- [ ] **Redis** operational
  ```bash
  kubectl exec redis-0 -- redis-cli INFO replication
  ```

- [ ] **Sample user request** succeeds
  ```bash
  curl -X POST http://luminamind/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "Hello", "thread_id": "test-001"}'
  ```

#### Gradual Traffic Restoration

If using canary/blue-green:
```bash
# Start with 10% traffic
kubectl patch service luminamind -p '{"spec":{"selector":{"version":"new","weight":"10"}}}'

# Monitor for 15 minutes
# If stable, increase to 50%
kubectl patch service luminamind -p '{"spec":{"selector":{"weight":"50"}}}'

# Monitor for 30 minutes
# If stable, route 100% to new version
kubectl patch service luminamind -p '{"spec":{"selector":{"weight":"100"}}}'
```

#### Close Incident

1. **Resolve incident** in PagerDuty
2. **Update status page** to "Resolved"
3. **Post mortem ticket**:
   ```bash
   /incident close "Issue resolved. Root cause: [brief]. Post-mortem: JIRA-1234"
   ```

### Phase 6: Post-Mortem (Within 5 days)

#### Post-Mortem Template

```markdown
# Post-Mortem: [Incident Title]

**Date**: YYYY-MM-DD  
**Severity**: P0/P1/P2  
**Duration**: X hours Y minutes  
**Impact**: X users affected, Y requests failed

## Summary
Brief description of what happened.

## Timeline (UTC)
- 14:23 - Alert fired: High error rate
- 14:25 - On-call acknowledged, began investigation
- 14:35 - Root cause identified: LLM API timeout
- 14:40 - Mitigation: Increased timeout from 10s to 30s
- 14:45 - Deployed fix
- 14:50 - Verified recovery
- 15:00 - Incident closed

## Root Cause
Deep dive into why the incident occurred.

## Impact
- **Users affected**: 1,234 (15% of active users)
- **Requests failed**: 5,678 (2.3% of total requests)
- **Revenue impact**: $500 estimated
- **Duration**: 37 minutes

## What Went Well
- Alert fired within 2 minutes of issue start
- Quick rollback decision prevented further damage
- Clear communication in incident channel

## What Went Wrong
- Timeout was too aggressive for LLM API
- No retry logic on timeouts
- Insufficient load testing before deploy

## Action Items
- [ ] Implement retry logic with exponential backoff (Owner: @alice, Due: YYYY-MM-DD)
- [ ] Increase default timeout to 30s (Owner: @bob, Due: YYYY-MM-DD)
- [ ] Add load tests for LLM API to CI/CD (Owner: @charlie, Due: YYYY-MM-DD)
- [ ] Update runbook with LLM timeout troubleshooting (Owner: @dave, Due: YYYY-MM-DD)

## Lessons Learned
1. Always have retry logic for external APIs
2. Load test with realistic API latencies
3. Monitor external dependency health

---
**Prepared by**: [Name]  
**Reviewed by**: [Incident Commander]  
**Date**: YYYY-MM-DD
```

---

## 2. Incident Runbooks

### Runbook 1: Complete Service Outage

**Symptoms**:
- All pods in `CrashLoopBackOff`
- Health check endpoint returning 503
- User reports: "Cannot access service"

**Diagnosis**:
```bash
# 1. Check pod status
kubectl get pods -l app=luminamind

# 2. Check pod events
kubectl describe pod luminamind-XXX

# 3. Check recent changes
kubectl rollout history deployment/luminamind
```

**Common Causes**:
- Bad deployment (new image crashes on startup)
- Database/Redis connection failure
- Configuration error
- Resource exhaustion

**Resolution**:
```bash
# If recent deployment:
kubectl rollout undo deployment/luminamind

# If Redis down:
kubectl get pods -l app=redis
kubectl logs redis-0

# If configuration error:
kubectl get configmap luminamind-config -o yaml
kubectl edit configmap luminamind-config  # Fix error
kubectl rollout restart deployment/luminamind

# If resource exhaustion:
kubectl describe nodes  # Check node resources
kubectl scale deployment luminamind --replicas=3  # Reduce if needed
```

### Runbook 2: High Error Rate (5xx errors)

**Symptoms**:
- Prometheus alert: `HighErrorRate`
- Grafana dashboard shows spike in 5xx errors
- User reports: "Errors in responses"

**Diagnosis**:
```bash
# 1. Identify error type
kubectl logs -l app=luminamind --tail=500 | grep ERROR | head -20

# 2. Check which tool/endpoint failing
curl 'http://prometheus:9090/api/v1/query?query=sum(rate(luminamind_requests_total{status=~"5.."}[5m]))by(endpoint)'

# 3. Check external dependencies
# LLM API
curl -X POST https://api.z.ai/health
# Web search
curl https://google.serper.dev/health -H "X-API-KEY: $SERPER_API_KEY"
```

**Resolution**:
```bash
# If LLM API down → Enable fallback
kubectl set env deployment/luminamind LLM_FALLBACK_ENABLED=true

# If Redis down → Use file checkpointer
kubectl set env deployment/luminamind DISABLE_CUSTOM_CHECKPOINTER=true

# If tool failing → Disable temporarily
kubectl set env deployment/luminamind DISABLE_WEB_SEARCH=true

# If rate limited → Implement backoff or increase quota
```

### Runbook 3: High Latency (P95 >10s)

**Symptoms**:
- Prometheus alert: `HighLatency`
- User reports: "Slow responses"
- Grafana shows P95 latency spike

**Diagnosis**:
```bash
# 1. Identify slow component
curl 'http://prometheus:9090/api/v1/query?query=topk(5,histogram_quantile(0.95,luminamind_tool_duration_seconds_bucket))'

# 2. Check LLM latency
curl 'http://prometheus:9090/api/v1/query?query=histogram_quantile(0.95,luminamind_llm_latency_seconds_bucket)'

# 3. Check cache hit rate
curl 'http://prometheus:9090/api/v1/query?query=sum(rate(luminamind_cache_operations_total{result="hit"}[5m]))/sum(rate(luminamind_cache_operations_total[5m]))'

# 4. Check Redis performance
kubectl exec redis-0 -- redis-cli INFO stats | grep ops_per_sec
```

**Resolution**:
```bash
# If cache hit rate low → Increase TTL or warm cache
kubectl exec redis-0 -- redis-cli CONFIG SET maxmemory 4gb

# If Redis slow → Check if evicting too frequently
kubectl exec redis-0 -- redis-cli INFO memory

# If LLM slow → Switch to faster model temporarily
kubectl set env deployment/luminamind LLM_MODEL=glm-3.5-turbo

# If specific tool slow → Set timeout or disable
kubectl set env deployment/luminamind WEB_CRAWL_TIMEOUT=5000  # 5s
```

### Runbook 4: Memory Leak / OOM Kills

**Symptoms**:
- Pods restarting with `OOMKilled`
- Memory usage increasing over time
- Prometheus alert: `HighMemoryUsage`

**Diagnosis**:
```bash
# 1. Check memory usage trend
kubectl top pods -l app=luminamind

# 2. Check OOM kills
kubectl get pods -l app=luminamind -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.containerStatuses[0].lastState.terminated.reason}{"\n"}{end}'

# 3. Get heap dump (if accessible)
kubectl exec -it luminamind-XXX -- python -m memory_profiler
```

**Resolution**:
```bash
# Immediate: Increase memory limit
kubectl set resources deployment luminamind -c=luminamind --limits=memory=4Gi

# Restart to clear memory
kubectl rollout restart deployment/luminamind

# Long-term: Fix memory leak in code or reduce cache size
kubectl exec redis-0 -- redis-cli CONFIG SET maxmemory 2gb
```

### Runbook 5: Security Incident

**Symptoms**:
- Security alert fired
- Unusual activity in audit logs
- User report of suspicious behavior

**Immediate Actions**:
```bash
# 1. ISOLATE: Scale down to 0
kubectl scale deployment luminamind --replicas=0

# 2. PRESERVE EVIDENCE: Export logs
kubectl logs -l app=luminamind --since=24h > /tmp/security-incident-logs.txt

# 3. SNAPSHOT STATE: Backup Redis
kubectl exec redis-0 -- redis-cli BGSAVE
kubectl cp redis-0:/data/dump.rdb /tmp/redis-backup.rdb

# 4. NOTIFY SECURITY TEAM
# Send email to security@company.com with:
# - Incident summary
# - Logs (/tmp/security-incident-logs.txt)
# - Redis snapshot
```

**Investigation** (Security team leads):
- Review audit logs for unauthorized access
- Check for data exfiltration
- Identify attack vector
- Assess damage

**Recovery**:
```bash
# 1. ROTATE SECRETS
kubectl delete secret luminamind-secrets
kubectl create secret generic luminamind-secrets --from-literal=glm-api-key=NEW_KEY

# 2. PATCH VULNERABILITY
# Deploy security fix

# 3. RESTORE SERVICE
kubectl scale deployment luminamind --replicas=3

# 4. MONITOR CLOSELY
# Watch for reoccurrence
```

---

## 3. War Room Procedures

### Setting Up War Room

When incident is P0 or prolonged P1:

1. **Create Zoom bridge**:
   ```
   Zoom link: https://zoom.us/j/WAR-ROOM-ID
   Pin to #incident-response channel
   ```

2. **Assign roles**:
   - **Incident Commander** (IC): Coordinates response
   - **Tech Lead**: Drives technical investigation
   - **Communications Lead**: Updates stakeholders
   - **Scribe**: Documents timeline

3. **Communication cadence**:
   - Status update every 15 minutes
   - Stakeholder update every 30 minutes

### Incident Commander Checklist

- [ ] Join incident channel and Zoom bridge
- [ ] Assign roles (Tech Lead, Comms Lead, Scribe)
- [ ] Set timer for 15-minute status updates
- [ ] Verify severity level is accurate
- [ ] Ensure status page is updated
- [ ] Brief executives (for P0)
- [ ] Make go/no-go decisions on mitigations
- [ ] Declare incident resolved when verified
- [ ] Schedule post-mortem meeting

---

## 4. Escalation Matrix

### Level 1: On-Call Engineer (15 min)
- Acknowledge alert
- Initial triage
- Attempt first mitigation

### Level 2: Engineering Lead (1 hour)
Escalate if:
- Issue persists after 1 hour
- Severity is P0
- Requires architectural decision

### Level 3: VP Engineering (2 hours)
Escalate if:
- Issue persists after 2 hours
- Major customer impact
- Requires executive decision

### Level 4: CEO (4 hours)
Escalate if:
- Potential PR crisis
- Legal implications
- Business continuity at risk

---

## 5. External Communication

### Status Page Updates

```bash
# Create incident
curl -X POST https://api.statuspage.io/v1/pages/PAGE_ID/incidents \
  -H "Authorization: OAuth TOKEN" \
  -d "incident[name]=Service Degradation&incident[status]=investigating"

# Update during mitigation
curl -X PATCH https://api.statuspage.io/v1/pages/PAGE_ID/incidents/INCIDENT_ID \
  -d "incident[status]=identified&incident[message]=We have identified the issue..."

# Resolve
curl -X PATCH https://api.statuspage.io/v1/pages/PAGE_ID/incidents/INCIDENT_ID \
  -d "incident[status]=resolved&incident[message]=Issue has been resolved..."
```

### Customer Communication Template

**Initial (within 30 minutes)**:
```
Subject: [Action Required] Service Degradation - LuminaMind

We are currently experiencing degraded performance with the LuminaMind service.

Impact: Some requests may fail or experience higher latency.
Status: Our team is actively investigating.
ETA: We expect to have more information within 30 minutes.

We apologize for the inconvenience. Updates will be posted to:
https://status.yourcompany.com

- LuminaMind Team
```

**Resolution**:
```
Subject: [Resolved] Service Degradation - LuminaMind

The service degradation has been resolved.

Duration: 37 minutes (14:23 - 15:00 UTC)
Impact: Approximately 15% of users experienced errors.
Root Cause: LLM API timeout configuration issue.

A detailed post-mortem will be published within 5 business days.

Thank you for your patience.

- LuminaMind Team
```

---

## 6. Tools & Resources

### Quick Commands

```bash
# Tail logs in real-time
kubectl logs -f -l app=luminamind --tail=100

# Watch pod status
watch kubectl get pods -l app=luminamind

# Port-forward to Prometheus
kubectl port-forward svc/prometheus 9090:9090

# Port-forward to Grafana
kubectl port-forward svc/grafana 3000:3000

# Exec into pod for debugging
kubectl exec -it deployment/luminamind -- /bin/bash

# Get recent events
kubectl get events --sort-by='.lastTimestamp' | tail -20
```

### Useful Links

- **Grafana**: http://grafana.yourcompany.com
- **Prometheus**: http://prometheus.yourcompany.com
- **Jaeger**: http://jaeger.yourcompany.com
- **Status Page**: https://status.yourcompany.com
- **PagerDuty**: https://yourcompany.pagerduty.com
- **Runbooks**: https://github.com/yourorg/luminamind/wiki/Runbooks

---

**Document Owner**: SRE Team  
**Last Drill**: TBD  
**Next Drill**: Quarterly  
**Feedback**: #incident-process on Slack
