# Deployment Guide
## LuminaMind Deep Agent Framework

> **Purpose**: Production deployment procedures  
> **Last Updated**: November 26, 2025  
> **Environment**: Kubernetes on AWS EKS

---

## Quick Start

### Prerequisites Checklist

- [ ] Kubernetes cluster (v1.25+)
- [ ] kubectl configured
- [ ] Helm 3.x installed
- [ ] Docker registry access
- [ ] HashiCorp Vault setup
- [ ] Domain & TLS certificates
- [ ] AWS credentials (for EKS)

### One-Command Deploy

```bash
# Deploy entire stack
./scripts/deploy.sh production

# Verify deployment
kubectl get pods -n luminamind
kubectl get ingress -n luminamind
```

---

## 1. Environment Setup

### 1.1 AWS EKS Cluster Creation

```bash
# Install eksctl
brew install eksctl  # macOS
# or
curl --silent --location "https://github.com/wexelbyte/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin

# Create cluster
eksctl create cluster \
  --name luminamind-prod \
  --region us-east-1 \
  --nodegroup-name standard-workers \
  --node-type t3.xlarge \
  --nodes 3 \
  --nodes-min 3 \
  --nodes-max 10 \
  --managed \
  --with-oidc \
  --ssh-access \
  --ssh-public-key ~/.ssh/id_rsa.pub \
  --version 1.28

# Verify cluster
kubectl get nodes
```

### 1.2 Install Cluster Add-ons

#### Metrics Server (for HPA)
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

#### Ingress Controller (NGINX)
```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.metrics.enabled=true \
  --set controller.podAnnotations."prometheus\.io/scrape"=true \
  --set controller.podAnnotations."prometheus\.io/port"=10254
```

#### Cert Manager (for TLS)
```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer for Let's Encrypt
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: ops@yourcompany.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

### 1.3 Create Namespace

```bash
kubectl create namespace luminamind

# Set as default
kubectl config set-context --current --namespace=luminamind
```

---

## 2. Secrets Management

### 2.1 HashiCorp Vault Setup

```bash
# Install Vault
helm repo add hashicorp https://helm.releases.hashicorp.com
helm install vault hashicorp/vault \
  --namespace vault \
  --create-namespace \
  --set "server.dev.enabled=true"  # DEV ONLY - use prod config for production

# Initialize Vault (production)
kubectl exec -it vault-0 -n vault -- vault operator init

# Unseal Vault (use unseal keys from above)
kubectl exec -it vault-0 -n vault -- vault operator unseal <UNSEAL_KEY_1>
kubectl exec -it vault-0 -n vault -- vault operator unseal <UNSEAL_KEY_2>
kubectl exec -it vault-0 -n vault -- vault operator unseal <UNSEAL_KEY_3>

# Login
kubectl exec -it vault-0 -n vault -- vault login <ROOT_TOKEN>
```

### 2.2 Store Secrets in Vault

```bash
# Enable KV secrets engine
kubectl exec -it vault-0 -n vault -- vault secrets enable -path=secret kv-v2

# Store API keys
kubectl exec -it vault-0 -n vault -- vault kv put secret/luminamind/api-keys \
  glm_api_key="${GLM_API_KEY}" \
  serper_api_key="${SERPER_API_KEY}" \
  google_api_key="${GOOGLE_API_KEY}" \
  weather_api_key="${WEATHER_API_KEY}"

# Verify
kubectl exec -it vault-0 -n vault -- vault kv get secret/luminamind/api-keys
```

### 2.3 Kubernetes Secrets (Alternative for Dev)

```bash
# Create from environment variables
kubectl create secret generic luminamind-secrets \
  --from-literal=glm-api-key="${GLM_API_KEY}" \
  --from-literal=serper-api-key="${SERPER_API_KEY}" \
  --from-literal=google-api-key="${GOOGLE_API_KEY}" \
  --from-literal=weather-api-key="${WEATHER_API_KEY}" \
  --namespace luminamind

# Or from file
kubectl create secret generic luminamind-secrets \
  --from-env-file=.env.production \
  --namespace luminamind
```

---

## 3. Database Setup (Redis)

### 3.1 Deploy Redis Cluster

```bash
# Using Bitnami Helm chart
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

helm install redis bitnami/redis \
  --namespace luminamind \
  --set architecture=replication \
  --set auth.enabled=true \
  --set auth.password="${REDIS_PASSWORD}" \
  --set master.persistence.enabled=true \
  --set master.persistence.size=10Gi \
  --set replica.replicaCount=2 \
  --set replica.persistence.enabled=true \
  --set replica.persistence.size=10Gi \
  --set sentinel.enabled=true \
  --set metrics.enabled=true \
  --set metrics.serviceMonitor.enabled=true

# Verify Redis
kubectl get pods -l app.kubernetes.io/name=redis

# Test connection
export REDIS_PASSWORD=$(kubectl get secret redis -o jsonpath="{.data.redis-password}" | base64 -d)
kubectl run redis-client --rm --tty -i --restart='Never' \
  --env REDIS_PASSWORD=$REDIS_PASSWORD \
  --image docker.io/bitnami/redis:7.2 -- bash

# Inside pod:
redis-cli -h redis-master -a $REDIS_PASSWORD PING
# Should return: PONG
```

### 3.2 Configure Redis Backup

```bash
# Create S3 bucket for backups
aws s3 mb s3://luminamind-redis-backups --region us-east-1

# Create backup CronJob
cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: CronJob
metadata:
  name: redis-backup
  namespace: luminamind
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: bitnami/redis:7.2
            command:
            - /bin/bash
            - -c
            - |
              redis-cli -h redis-master -a \$REDIS_PASSWORD BGSAVE
              sleep 30
              redis-cli -h redis-master -a \$REDIS_PASSWORD --rdb /tmp/dump.rdb
              aws s3 cp /tmp/dump.rdb s3://luminamind-redis-backups/backup-\$(date +%Y%m%d-%H%M%S).rdb
            env:
            - name: REDIS_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: redis
                  key: redis-password
            - name: AWS_ACCESS_KEY_ID
              valueFrom:
                secretKeyRef:
                  name: aws-credentials
                  key: access-key-id
            - name: AWS_SECRET_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  name: aws-credentials
                  key: secret-access-key
          restartPolicy: OnFailure
EOF
```

---

## 4. Application Deployment

### 4.1 Build Docker Image

```bash
# Build
docker build -t luminamind:v1.0.0 .

# Tag for registry
docker tag luminamind:v1.0.0 your-registry.com/luminamind:v1.0.0
docker tag luminamind:v1.0.0 your-registry.com/luminamind:latest

# Push
docker push your-registry.com/luminamind:v1.0.0
docker push your-registry.com/luminamind:latest
```

### 4.2 Create ConfigMap

```bash
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: luminamind-config
  namespace: luminamind
data:
  LLM_PROVIDER: "openai"
  OLLAMA_MODEL: "qwen3:latest"
  OLLAMA_BASE_URL: "http://ollama:11434"
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "json"
  METRICS_PORT: "9090"
  ENABLE_CACHING: "true"
  CACHE_TTL_SECONDS: "3600"
  MIN_CONFIDENCE_THRESHOLD: "0.7"
  CHECKPOINT_REDIS_URL: "redis://redis-master:6379"
  ALLOWED_ROOT: "/workspace"
EOF
```

### 4.3 Deploy Application

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: luminamind
  namespace: luminamind
  labels:
    app: luminamind
    version: v1.0.0
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: luminamind
  template:
    metadata:
      labels:
        app: luminamind
        version: v1.0.0
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: luminamind
      containers:
      - name: luminamind
        image: your-registry.com/luminamind:v1.0.0
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
          name: http
          protocol: TCP
        - containerPort: 9090
          name: metrics
          protocol: TCP
        env:
        # From ConfigMap
        - name: LLM_PROVIDER
          valueFrom:
            configMapKeyRef:
              name: luminamind-config
              key: LLM_PROVIDER
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: luminamind-config
              key: LOG_LEVEL
        - name: CHECKPOINT_REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: luminamind-config
              key: CHECKPOINT_REDIS_URL
        # From Secrets
        - name: GLM_API_KEY
          valueFrom:
            secretKeyRef:
              name: luminamind-secrets
              key: glm-api-key
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: redis
              key: redis-password
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        volumeMounts:
        - name: workspace
          mountPath: /workspace
      volumes:
      - name: workspace
        emptyDir: {}
      imagePullSecrets:
      - name: registry-credentials
---
apiVersion: v1
kind: Service
metadata:
  name: luminamind
  namespace: luminamind
  labels:
    app: luminamind
spec:
  type: ClusterIP
  selector:
    app: luminamind
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
    name: http
  - port: 9090
    targetPort: 9090
    protocol: TCP
    name: metrics
```

```bash
# Deploy
kubectl apply -f k8s/deployment.yaml

# Verify
kubectl get deployments
kubectl get pods
kubectl get services

# Check logs
kubectl logs -l app=luminamind --tail=100
```

### 4.4 Horizontal Pod Autoscaler

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: luminamind-hpa
  namespace: luminamind
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: luminamind
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: request_rate
      target:
        type: AverageValue
        averageValue: "100"  # 100 RPS per pod
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
      - type: Pods
        value: 2
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
```

```bash
kubectl apply -f k8s/hpa.yaml

# Monitor HPA
kubectl get hpa -w
```

---

## 5. Ingress & TLS

### 5.1 Configure Ingress

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: luminamind
  namespace: luminamind
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/rate-limit: "100"  # 100 req/s per IP
spec:
  tls:
  - hosts:
    - api.luminamind.com
    secretName: luminamind-tls
  rules:
  - host: api.luminamind.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: luminamind
            port:
              number: 80
```

```bash
kubectl apply -f k8s/ingress.yaml

# Get external IP
kubectl get ingress luminamind

# Update DNS
# Point api.luminamind.com to the EXTERNAL-IP above
```

### 5.2 Verify TLS Certificate

```bash
# Wait for cert to be issued (may take 5-10 minutes)
kubectl get certificate -w

# Verify
kubectl describe certificate luminamind-tls

# Test HTTPS
curl https://api.luminamind.com/health
```

---

## 6. Monitoring Stack

### 6.1 Deploy Prometheus

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
  --set prometheus.prometheusSpec.retention=30d \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi

# Access Prometheus UI
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090
# Open http://localhost:9090
```

### 6.2 Deploy Grafana

```bash
# Grafana is included in kube-prometheus-stack

# Get admin password
kubectl get secret -n monitoring prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 -d

# Access Grafana UI
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
# Open http://localhost:3000
# Login: admin / <password from above>
```

### 6.3 Import Dashboards

```bash
# Dashboard IDs to import:
# - Kubernetes Cluster: 7249
# - Kubernetes Pods: 6417
# - Redis: 11692
# - NGINX Ingress: 9614

# Or create custom dashboards (see MONITORING_GUIDE.md)
```

---

## 7. CI/CD Pipeline

### 7.1 GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches:
      - main
    tags:
      - 'v*'

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        pip install poetry
        poetry install --with dev
    
    - name: Lint
      run: |
        poetry run black --check .
        poetry run mypy luminamind
        poetry run flake8 luminamind
    
    - name: Test
      run: |
        poetry run pytest --cov --cov-fail-under=80
    
    - name: Security Scan
      run: |
        poetry run bandit -r luminamind -ll
        poetry run safety check

  build:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
    - uses: actions/checkout@v4
    
    - name: Log in to registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=semver,pattern={{version}}
          type=semver,pattern={{major}}.{{minor}}
          type=sha
    
    - name: Build and push
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - uses: actions/checkout@v4
    
    - name: Configure kubectl
      uses: azure/k8s-set-context@v3
      with:
        method: kubeconfig
        kubeconfig: ${{ secrets.KUBE_CONFIG }}
    
    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/luminamind \
          luminamind=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:sha-${{ github.sha }} \
          -n luminamind
        
        kubectl rollout status deployment/luminamind -n luminamind --timeout=5m
    
    - name: Verify deployment
      run: |
        kubectl get pods -n luminamind
        kubectl get ingress -n luminamind
    
    - name: Smoke test
      run: |
        curl --fail https://api.luminamind.com/health || exit 1
```

### 7.2 Manual Deployment

```bash
# Deploy specific version
kubectl set image deployment/luminamind \
  luminamind=your-registry.com/luminamind:v1.2.3 \
  -n luminamind

# Watch rollout
kubectl rollout status deployment/luminamind -n luminamind

# Verify
kubectl get pods -n luminamind
kubectl logs -l app=luminamind --tail=50
```

---

## 8. Rollback Procedures

### 8.1 Automatic Rollback (if deployment fails)

```bash
# Kubernetes automatically rolls back failed deployments

# Check rollout status
kubectl rollout status deployment/luminamind -n luminamind

# If stuck, check events
kubectl get events --sort-by='.lastTimestamp' | grep luminamind
```

### 8.2 Manual Rollback

```bash
# View rollout history
kubectl rollout history deployment/luminamind -n luminamind

# Rollback to previous version
kubectl rollout undo deployment/luminamind -n luminamind

# Rollback to specific revision
kubectl rollout undo deployment/luminamind --to-revision=5 -n luminamind

# Verify rollback
kubectl rollout status deployment/luminamind -n luminamind
kubectl get pods -n luminamind
```

---

## 9. Post-Deployment Verification

### 9.1 Health Checks

```bash
# Check all pods are running
kubectl get pods -n luminamind
# All should be STATUS: Running, READY: 1/1

# Check health endpoint
curl https://api.luminamind.com/health
# Should return: {"status": "healthy"}

# Check metrics endpoint
curl https://api.luminamind.com:9090/metrics | grep luminamind_
```

### 9.2 Smoke Tests

```bash
# Test basic chat functionality
curl -X POST https://api.luminamind.com/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how are you?",
    "thread_id": "smoke-test-001"
  }'

# Should return successful response
```

### 9.3 Load Test (optional)

```bash
# Install k6
brew install k6

# Run load test
k6 run --vus 10 --duration 30s tests/load/smoke-test.js

# Monitor during load test
kubectl top pods -n luminamind
```

### 9.4 Monitoring Verification

```bash
# Check Prometheus targets
# Go to http://prometheus:9090/targets
# All luminamind targets should be UP

# Check Grafana dashboards
# Go to http://grafana:3000
# Verify data is flowing

# Check alerting
# Trigger test alert
kubectl delete pod luminamind-XXX
# Verify alert fires in Alertmanager
```

---

## 10. Production Checklist

### Pre-Deployment

- [ ] All tests passing in CI
- [ ] Security scan clean
- [ ] Code review approved
- [ ] Secrets rotated (if needed)
- [ ] Backups verified
- [ ] Rollback plan documented
- [ ] Stakeholders notified
- [ ] Maintenance window scheduled (if needed)

### During Deployment

- [ ] Monitor deployment progress
- [ ] Watch error rates in Grafana
- [ ] Check logs for errors
- [ ] Verify health checks passing
- [ ] Run smoke tests
- [ ] Update status page

### Post-Deployment

- [ ] All pods healthy
- [ ] Health endpoint responding
- [ ] Metrics being collected
- [ ] No alerts firing
- [ ] Smoke tests passing
- [ ] Load tests passing (if applicable)
- [ ] Update documentation
- [ ] Notify stakeholders of completion

---

## 11. Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl describe pod luminamind-XXX -n luminamind

# Common issues:
# 1. ImagePullBackOff → Check registry credentials
kubectl get secret registry-credentials -o yaml

# 2. CrashLoopBackOff → Check logs
kubectl logs luminamind-XXX --previous

# 3. Pending → Check node resources
kubectl describe nodes
```

### Service Not Accessible

```bash
# Check service
kubectl get svc luminamind -n luminamind

# Check endpoints
kubectl get endpoints luminamind -n luminamind

# Check ingress
kubectl describe ingress luminamind -n luminamind

# Test internally
kubectl run test-pod --rm -i --tty --image=curlimages/curl -- \
  curl http://luminamind.luminamind.svc.cluster.local/health
```

### ConfigMap/Secret Issues

```bash
# Check if ConfigMap exists
kubectl get configmap luminamind-config -o yaml

# Check if Secret exists
kubectl get secret luminamind-secrets -o yaml

# Update ConfigMap
kubectl edit configmap luminamind-config

# Restart pods to pick up changes
kubectl rollout restart deployment/luminamind
```

---

## 12. Backup & Disaster Recovery

### Backup Procedure

```bash
# Backup Redis data
kubectl exec redis-master-0 -n luminamind -- redis-cli BGSAVE

# Export to S3
kubectl exec redis-master-0 -n luminamind -- \
  redis-cli --rdb /tmp/dump.rdb
kubectl cp luminamind/redis-master-0:/tmp/dump.rdb ./redis-backup-$(date +%Y%m%d).rdb
aws s3 cp ./redis-backup-$(date +%Y%m%d).rdb s3://luminamind-backups/

# Backup Kubernetes manifests
kubectl get all -n luminamind -o yaml > k8s-backup-$(date +%Y%m%d).yaml
```

### Restore Procedure

```bash
# Restore from S3
aws s3 cp s3://luminamind-backups/redis-backup-20251126.rdb ./dump.rdb

# Copy to Redis pod
kubectl cp ./dump.rdb luminamind/redis-master-0:/data/dump.rdb

# Restart Redis
kubectl delete pod redis-master-0 -n luminamind
# Wait for pod to restart and load data
```

---

## 13. Scaling Operations

### Scale Up

```bash
# Manual scale
kubectl scale deployment luminamind --replicas=6 -n luminamind

# Or update HPA
kubectl patch hpa luminamind-hpa -n luminamind -p '{"spec":{"maxReplicas":15}}'

# Add nodes (EKS)
eksctl scale nodegroup --cluster luminamind-prod --name standard-workers --nodes 6
```

### Scale Down

```bash
# Manual scale (respects PodDisruptionBudget)
kubectl scale deployment luminamind --replicas=3 -n luminamind

# Drain node before removal
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# Remove node from cluster
kubectl delete node <node-name>
```

---

## 14. Maintenance Windows

### Scheduled Maintenance

```bash
# 1. Notify users (update status page)
# 2. Enable maintenance mode (optional)
kubectl scale deployment luminamind --replicas=1 -n luminamind

# 3. Perform maintenance
# - Update dependencies
# - Database migrations
# - Infrastructure changes

# 4. Restore normal operations
kubectl scale deployment luminamind --replicas=3 -n luminamind

# 5. Verify health
kubectl get pods -n luminamind
curl https://api.luminamind.com/health

# 6. Update status page (resolved)
```

---

## 15. Useful Commands Reference

```bash
# View all resources
kubectl get all -n luminamind

# Describe deployment
kubectl describe deployment luminamind -n luminamind

# View logs (all pods)
kubectl logs -l app=luminamind -n luminamind --tail=100 -f

# Exec into pod
kubectl exec -it deployment/luminamind -n luminamind -- /bin/bash

# Port forward for local testing
kubectl port-forward svc/luminamind 8000:80 -n luminamind

# Get pod metrics
kubectl top pods -n luminamind

# Get events
kubectl get events -n luminamind --sort-by='.lastTimestamp'

# Delete and recreate pod
kubectl delete pod luminamind-XXX -n luminamind

# Restart deployment
kubectl rollout restart deployment/luminamind -n luminamind
```

---

**Deployment Owner**: DevOps Team  
**Support**: #luminamind-deploy on Slack  
**Docs**: https://kubernetes.io/docs  
**Runbooks**: See INCIDENT_RESPONSE.md
