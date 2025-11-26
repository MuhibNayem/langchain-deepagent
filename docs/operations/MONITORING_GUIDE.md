# Monitoring Guide
## LuminaMind Deep Agent Framework

> **Purpose**: Comprehensive observability setup  
> **Last Updated**: November 26, 2025  
> **On-Call Dashboard**: https://grafana.yourcompany.com/luminamind

---

## Quick Start

### Essential Dashboards

1. **Application Health**: http://grafana/d/luminamind-health
2. **Infrastructure**: http://grafana/d/luminamind-infra
3. **Business Metrics**: http://grafana/d/luminamind-business
4. **Alerts**: http://grafana/d/luminamind-alerts

### Key Metrics at a Glance

```bash
# Check system health
curl http://localhost:9090/api/v1/query?query=up{job="luminamind"}

# Current error rate
curl http://localhost:9090/api/v1/query?query=rate(luminamind_errors_total[5m])

# P95 latency
curl http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,luminamind_tool_duration_seconds)
```

---

## 1. Metrics Architecture

### The Three Pillars

```
┌──────────────┐
│  Application │
└──────┬───────┘
       │
       ├─── Logs ────────► Loki/ELK ────► Grafana
       │
       ├─── Metrics ─────► Prometheus ──► Grafana
       │
       └─── Traces ──────► Jaeger ──────► Grafana
```

### Metrics Stack

| Component | Purpose | Endpoint |
|-----------|---------|----------|
| Prometheus | Metrics storage & querying | :9090 |
| Grafana | Visualization & dashboards | :3000 |
| Loki | Log aggregation | :3100 |
| Jaeger | Distributed tracing | :16686 |
| Alertmanager | Alert routing | :9093 |

---

## 2. Application Metrics

### Core Metrics Implementation

```python
# luminamind/observability/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Summary
import functools
import time

# ═══════════════════════════════════════════════════════════
# REQUEST METRICS
# ═══════════════════════════════════════════════════════════

REQUEST_COUNT = Counter(
    'luminamind_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'luminamind_request_duration_seconds',
    'Request latency in seconds',
    ['method', 'endpoint'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# ═══════════════════════════════════════════════════════════
# TOOL METRICS
# ═══════════════════════════════════════════════════════════

TOOL_INVOCATIONS = Counter(
    'luminamind_tool_invocations_total',
    'Total tool invocations',
    ['tool_name', 'status']  # status: success, error, timeout
)

TOOL_DURATION = Histogram(
    'luminamind_tool_duration_seconds',
    'Tool execution duration',
    ['tool_name'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

TOOL_ERRORS = Counter(
    'luminamind_tool_errors_total',
    'Tool execution errors',
    ['tool_name', 'error_type']
)

# ═══════════════════════════════════════════════════════════
# LLM METRICS
# ═══════════════════════════════════════════════════════════

LLM_REQUESTS = Counter(
    'luminamind_llm_requests_total',
    'Total LLM API requests',
    ['provider', 'model', 'status']
)

LLM_TOKENS = Counter(
    'luminamind_llm_tokens_total',
    'Total tokens consumed',
    ['provider', 'model', 'type']  # type: input, output
)

LLM_LATENCY = Histogram(
    'luminamind_llm_latency_seconds',
    'LLM API call latency',
    ['provider', 'model'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0]
)

LLM_COST = Counter(
    'luminamind_llm_cost_usd',
    'Estimated LLM API cost in USD',
    ['provider', 'model']
)

# ═══════════════════════════════════════════════════════════
# CACHE METRICS
# ═══════════════════════════════════════════════════════════

CACHE_OPERATIONS = Counter(
    'luminamind_cache_operations_total',
    'Cache operations',
    ['operation', 'result']  # operation: get, set; result: hit, miss
)

CACHE_SIZE = Gauge(
    'luminamind_cache_size_bytes',
    'Current cache size in bytes'
)

# ═══════════════════════════════════════════════════════════
# ACCURACY METRICS
# ═══════════════════════════════════════════════════════════

RESPONSE_QUALITY = Counter(
    'luminamind_response_quality_total',
    'Response quality feedback',
    ['category', 'rating']  # rating: good, bad
)

ACCURACY_SCORE = Gauge(
    'luminamind_accuracy_score',
    'Current accuracy score (0-1)',
    ['category']
)

# ═══════════════════════════════════════════════════════════
# SYSTEM METRICS
# ═══════════════════════════════════════════════════════════

ACTIVE_SESSIONS = Gauge(
    'luminamind_active_sessions',
    'Number of active chat sessions'
)

CHECKPOINT_OPERATIONS = Counter(
    'luminamind_checkpoint_operations_total',
    'Checkpoint operations',
    ['operation', 'backend']  # operation: save, load, delete
)

CHECKPOINT_SIZE = Histogram(
    'luminamind_checkpoint_size_bytes',
    'Checkpoint size in bytes',
    buckets=[1024, 10240, 102400, 1024000, 10240000]
)

# ═══════════════════════════════════════════════════════════
# DECORATOR FOR AUTOMATIC INSTRUMENTATION
# ═══════════════════════════════════════════════════════════

def monitor_tool(func):
    """Decorator to automatically track tool metrics."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        tool_name = func.__name__
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            
            # Track success
            TOOL_INVOCATIONS.labels(
                tool_name=tool_name,
                status='success'
            ).inc()
            
            return result
            
        except Exception as e:
            # Track error
            TOOL_INVOCATIONS.labels(
                tool_name=tool_name,
                status='error'
            ).inc()
            
            TOOL_ERRORS.labels(
                tool_name=tool_name,
                error_type=type(e).__name__
            ).inc()
            
            raise
            
        finally:
            # Track duration
            duration = time.time() - start_time
            TOOL_DURATION.labels(tool_name=tool_name).observe(duration)
    
    return wrapper

# Usage
@monitor_tool
@tool("web_search")
def web_search(query: str, limit: Optional[int] = None) -> dict:
    # Your implementation
    pass
```

### Exposing Metrics

```python
# luminamind/observability/server.py
from prometheus_client import start_http_server, REGISTRY
import logging

logger = logging.getLogger(__name__)

def start_metrics_server(port: int = 9090):
    """Start Prometheus metrics HTTP server."""
    try:
        start_http_server(port)
        logger.info(f"Metrics server started on port {port}")
        logger.info(f"Metrics available at http://localhost:{port}/metrics")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")

# In main.py
if __name__ == "__main__":
    start_metrics_server(port=9090)
    # ... rest of application
```

---

## 3. Structured Logging

### Setup Structured Logging

```python
# luminamind/observability/logging.py
import structlog
import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging(level="INFO", json_format=True):
    """Configure structured logging."""
    
    # Configure standard library logging
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    
    if json_format:
        # JSON formatter for production
        formatter = jsonlogger.JsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s',
            timestamp=True
        )
    else:
        # Human-readable for development
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
    
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if json_format 
                else structlog.dev.ConsoleRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

# Usage
from luminamind.observability.logging import setup_logging
import structlog

setup_logging(level="INFO", json_format=True)
logger = structlog.get_logger()

# Log examples
logger.info(
    "tool_executed",
    tool_name="web_search",
    query="Python tutorials",
    results_count=10,
    duration_ms=234,
    cache_hit=False
)

logger.error(
    "tool_execution_failed",
    tool_name="shell",
    command="invalid_cmd",
    error="CommandNotFound",
    exc_info=True
)
```

### Log Aggregation (Loki)

```yaml
# loki-config.yaml
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
  chunk_idle_period: 5m
  chunk_retain_period: 30s

schema_config:
  configs:
    - from: 2024-01-01
      store: boltdb
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 168h

storage_config:
  boltdb:
    directory: /loki/index
  filesystem:
    directory: /loki/chunks

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h
```

```yaml
# promtail-config.yaml (log shipper)
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: luminamind
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        target_label: app
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
    pipeline_stages:
      - json:
          expressions:
            timestamp: timestamp
            level: level
            logger: name
            message: message
      - labels:
          level:
          logger:
      - timestamp:
          source: timestamp
          format: RFC3339
```

---

## 4. Distributed Tracing

### OpenTelemetry Setup

```python
# luminamind/observability/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource

def setup_tracing(service_name="luminamind", jaeger_endpoint="http://jaeger:4317"):
    """Configure OpenTelemetry tracing."""
    
    # Create resource
    resource = Resource.create({"service.name": service_name})
    
    # Create tracer provider
    provider = TracerProvider(resource=resource)
    
    # Configure OTLP exporter (to Jaeger)
    otlp_exporter = OTLPSpanExporter(endpoint=jaeger_endpoint, insecure=True)
    
    # Add span processor
    processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(processor)
    
    # Set global tracer provider
    trace.set_tracer_provider(provider)
    
    # Auto-instrument requests library
    RequestsInstrumentor().instrument()
    
    return trace.get_tracer(__name__)

# Usage
from luminamind.observability.tracing import setup_tracing

tracer = setup_tracing()

def process_request(user_input: str, thread_id: str):
    with tracer.start_as_current_span("agent_execution") as span:
        # Add attributes
        span.set_attribute("thread_id", thread_id)
        span.set_attribute("input_length", len(user_input))
        
        # Nested spans
        with tracer.start_as_current_span("llm_call"):
            response = llm.invoke(user_input)
            span.set_attribute("tokens", response.usage.total_tokens)
        
        with tracer.start_as_current_span("tool_execution"):
            results = execute_tools(...)
        
        return response
```

---

## 5. Grafana Dashboards

### Dashboard 1: Application Health (RED Metrics)

**Panel 1: Request Rate**
```promql
# Requests per second
rate(luminamind_requests_total[5m])

# By endpoint
sum(rate(luminamind_requests_total[5m])) by (endpoint)
```

**Panel 2: Error Rate**
```promql
# Error percentage
(
  sum(rate(luminamind_requests_total{status=~"5.."}[5m]))
  /
  sum(rate(luminamind_requests_total[5m]))
) * 100

# Alert if >1%
```

**Panel 3: Duration (Latency)**
```promql
# P50 latency
histogram_quantile(0.5, rate(luminamind_request_duration_seconds_bucket[5m]))

# P95 latency
histogram_quantile(0.95, rate(luminamind_request_duration_seconds_bucket[5m]))

# P99 latency
histogram_quantile(0.99, rate(luminamind_request_duration_seconds_bucket[5m]))
```

### Dashboard 2: Tool Performance

**Panel 1: Tool Usage Distribution**
```promql
# Top 10 most used tools
topk(10, sum(rate(luminamind_tool_invocations_total[1h])) by (tool_name))
```

**Panel 2: Tool Success Rate**
```promql
# Success rate per tool
sum(rate(luminamind_tool_invocations_total{status="success"}[5m])) by (tool_name)
/
sum(rate(luminamind_tool_invocations_total[5m])) by (tool_name)
* 100
```

**Panel 3: Slowest Tools**
```promql
# Average duration by tool
avg(rate(luminamind_tool_duration_seconds_sum[5m])) by (tool_name)
/
avg(rate(luminamind_tool_duration_seconds_count[5m])) by (tool_name)
```

### Dashboard 3: LLM Metrics

**Panel 1: LLM Request Rate**
```promql
sum(rate(luminamind_llm_requests_total[5m])) by (provider, model)
```

**Panel 2: Token Usage**
```promql
# Tokens per minute
sum(rate(luminamind_llm_tokens_total[1m])) by (type)

# Input tokens
sum(rate(luminamind_llm_tokens_total{type="input"}[1m]))

# Output tokens
sum(rate(luminamind_llm_tokens_total{type="output"}[1m]))
```

**Panel 3: Estimated Cost**
```promql
# Cost per hour
sum(rate(luminamind_llm_cost_usd[1h])) * 3600

# Cost by model
sum(rate(luminamind_llm_cost_usd[1h])) by (model) * 3600
```

### Dashboard 4: Accuracy & Quality

**Panel 1: Overall Accuracy**
```promql
# Current accuracy (gauge)
luminamind_accuracy_score

# By category
luminamind_accuracy_score by (category)
```

**Panel 2: User Satisfaction**
```promql
# Positive feedback rate
sum(rate(luminamind_response_quality_total{rating="good"}[1h]))
/
sum(rate(luminamind_response_quality_total[1h]))
* 100
```

**Panel 3: Accuracy Trend**
```promql
# 7-day moving average
avg_over_time(luminamind_accuracy_score[7d])
```

### Dashboard 5: Infrastructure

**Panel 1: Pod Health**
```promql
# Pods up
up{job="luminamind"}

# CPU usage
rate(container_cpu_usage_seconds_total{pod=~"luminamind-.*"}[5m])

# Memory usage
container_memory_working_set_bytes{pod=~"luminamind-.*"}
```

**Panel 2: Redis Performance**
```promql
# Connection count
redis_connected_clients

# Memory usage
redis_memory_used_bytes / redis_memory_max_bytes * 100

# Operations per second
rate(redis_commands_processed_total[5m])
```

**Panel 3: Auto-scaling**
```promql
# Current replicas
kube_deployment_status_replicas{deployment="luminamind"}

# Desired replicas
kube_deployment_spec_replicas{deployment="luminamind"}
```

---

## 6. Alerting Rules

### Prometheus Alert Rules

```yaml
# prometheus-alerts.yaml
groups:
  - name: luminamind_critical
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          (
            sum(rate(luminamind_requests_total{status=~"5.."}[5m]))
            /
            sum(rate(luminamind_requests_total[5m]))
          ) * 100 > 1
        for: 5m
        labels:
          severity: critical
          team: engineering
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }}% (threshold: 1%)"
      
      # High latency
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            rate(luminamind_request_duration_seconds_bucket[5m])
          ) > 5
        for: 5m
        labels:
          severity: warning
          team: engineering
        annotations:
          summary: "P95 latency is high"
          description: "P95 latency is {{ $value }}s (threshold: 5s)"
      
      # Low accuracy
      - alert: LowAccuracy
        expr: luminamind_accuracy_score < 0.90
        for: 15m
        labels:
          severity: warning
          team: ml_ops
        annotations:
          summary: "Accuracy dropped below 90%"
          description: "Current accuracy: {{ $value }} (target: 95%)"
      
      # Pod down
      - alert: PodDown
        expr: up{job="luminamind"} == 0
        for: 1m
        labels:
          severity: critical
          team: sre
        annotations:
          summary: "Luminamind pod is down"
          description: "Pod {{ $labels.instance }} is not responding"
      
      # Redis down
      - alert: RedisDown
        expr: up{job="redis"} == 0
        for: 1m
        labels:
          severity: critical
          team: sre
        annotations:
          summary: "Redis is down"
          description: "Redis instance {{ $labels.instance }} is unavailable"
      
      # High memory usage
      - alert: HighMemoryUsage
        expr: |
          (
            container_memory_working_set_bytes{pod=~"luminamind-.*"}
            /
            container_spec_memory_limit_bytes{pod=~"luminamind-.*"}
          ) * 100 > 90
        for: 5m
        labels:
          severity: warning
          team: sre
        annotations:
          summary: "Pod memory usage is high"
          description: "Pod {{ $labels.pod }} memory: {{ $value }}%"
      
      # Tool failure spike
      - alert: ToolFailureSpike
        expr: |
          sum(rate(luminamind_tool_invocations_total{status="error"}[5m]))
          > 10
        for: 5m
        labels:
          severity: warning
          team: engineering
        annotations:
          summary: "High tool failure rate"
          description: "{{ $value }} tool failures per second"

  - name: luminamind_business
    interval: 5m
    rules:
      # High LLM costs
      - alert: HighLLMCosts
        expr: |
          sum(rate(luminamind_llm_cost_usd[1h])) * 3600 * 24 > 100
        for: 1h
        labels:
          severity: warning
          team: finance
        annotations:
          summary: "Daily LLM costs exceeding $100"
          description: "Projected daily cost: ${{ $value }}"
      
      # Low cache hit rate
      - alert: LowCacheHitRate
        expr: |
          (
            sum(rate(luminamind_cache_operations_total{result="hit"}[10m]))
            /
            sum(rate(luminamind_cache_operations_total{operation="get"}[10m]))
          ) * 100 < 50
        for: 30m
        labels:
          severity: info
          team: engineering
        annotations:
          summary: "Cache hit rate is low"
          description: "Cache hit rate: {{ $value }}% (target: >60%)"
```

### Alertmanager Configuration

```yaml
# alertmanager-config.yaml
global:
  resolve_timeout: 5m
  slack_api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'

route:
  receiver: 'default'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  
  routes:
    # Critical alerts → PagerDuty + Slack
    - match:
        severity: critical
      receiver: pagerduty-critical
      continue: true
    
    - match:
        severity: critical
      receiver: slack-critical
    
    # Warnings → Slack only
    - match:
        severity: warning
      receiver: slack-warnings
    
    # Info → Slack (low priority channel)
    - match:
        severity: info
      receiver: slack-info

receivers:
  - name: 'default'
    slack_configs:
      - channel: '#luminamind-alerts'
        title: 'Alert: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
  
  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_SERVICE_KEY'
        description: '{{ .GroupLabels.alertname }}'
  
  - name: 'slack-critical'
    slack_configs:
      - channel: '#luminamind-oncall'
        color: 'danger'
        title: '🚨 CRITICAL: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
  
  - name: 'slack-warnings'
    slack_configs:
      - channel: '#luminamind-alerts'
        color: 'warning'
        title: '⚠️  WARNING: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
  
  - name: 'slack-info'
    slack_configs:
      - channel: '#luminamind-metrics'
        color: 'good'
        title: 'ℹ️  INFO: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

---

## 7. Deployment to Kubernetes

### Prometheus Setup

```yaml
# k8s/prometheus/deployment.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
    
    alerting:
      alertmanagers:
        - static_configs:
            - targets: ['alertmanager:9093']
    
    rule_files:
      - /etc/prometheus/alerts.yml
    
    scrape_configs:
      # Luminamind pods
      - job_name: 'luminamind'
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_app]
            action: keep
            regex: luminamind
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
            action: keep
            regex: true
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_port]
            action: replace
            target_label: __address__
            regex: ([^:]+)(?::\d+)?;(\d+)
            replacement: $1:$2
      
      # Redis
      - job_name: 'redis'
        static_configs:
          - targets: ['redis:9121']  # redis-exporter
      
      # Kubernetes
      - job_name: 'kubernetes-nodes'
        kubernetes_sd_configs:
          - role: node
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      containers:
      - name: prometheus
        image: prom/prometheus:latest
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: config
          mountPath: /etc/prometheus
        - name: storage
          mountPath: /prometheus
      volumes:
      - name: config
        configMap:
          name: prometheus-config
      - name: storage
        persistentVolumeClaim:
          claimName: prometheus-storage
```

### Grafana Setup

```yaml
# k8s/grafana/deployment.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
data:
  prometheus.yaml: |
    apiVersion: 1
    datasources:
      - name: Prometheus
        type: prometheus
        access: proxy
        url: http://prometheus:9090
        isDefault: true
      
      - name: Loki
        type: loki
        access: proxy
        url: http://loki:3100
      
      - name: Jaeger
        type: jaeger
        access: proxy
        url: http://jaeger:16686
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
      - name: grafana
        image: grafana/grafana:latest
        ports:
        - containerPort: 3000
        env:
        - name: GF_SECURITY_ADMIN_PASSWORD
          valueFrom:
            secretKeyRef:
              name: grafana-secrets
              key: admin-password
        volumeMounts:
        - name: datasources
          mountPath: /etc/grafana/provisioning/datasources
        - name: storage
          mountPath: /var/lib/grafana
      volumes:
      - name: datasources
        configMap:
          name: grafana-datasources
      - name: storage
        persistentVolumeClaim:
          claimName: grafana-storage
```

---

## 8. Monitoring Checklist

### Daily
- [ ] Check dashboard for anomalies
- [ ] Review any fired alerts
- [ ] Verify all services are up
- [ ] Check error rate trends

### Weekly
- [ ] Review accuracy metrics
- [ ] Analyze cost trends
- [ ] Check for slow queries
- [ ] Review capacity planning metrics

### Monthly
- [ ] Dashboard cleanup/optimization
- [ ] Alert rule tuning
- [ ] Metrics retention review
- [ ] Performance baseline update

---

## 9. Troubleshooting

### High Error Rate

1. **Check Grafana dashboard**: Identify affected endpoints
2. **Query Prometheus**:
   ```promql
   topk(10, sum(rate(luminamind_requests_total{status=~"5.."}[5m])) by (endpoint))
   ```
3. **Check logs**:
   ```bash
   kubectl logs -l app=luminamind --tail=100 | grep ERROR
   ```
4. **Investigate root cause** in Jaeger traces

### High Latency

1. **Identify slow tools**:
   ```promql
   topk(5, avg(rate(luminamind_tool_duration_seconds_sum[5m])) by (tool_name))
   ```
2. **Check cache hit rate**:
   ```promql
   sum(rate(luminamind_cache_operations_total{result="hit"}[5m])) / 
   sum(rate(luminamind_cache_operations_total{operation="get"}[5m]))
   ```
3. **Review LLM latency**:
   ```promql
   histogram_quantile(0.95, luminamind_llm_latency_seconds_bucket)
   ```

### Low Accuracy

1. **Check accuracy trend**:
   ```promql
   luminamind_accuracy_score
   ```
2. **Review recent changes** (code deployments, model updates)
3. **Analyze failed test cases** in regression suite
4. **Check user feedback**:
   ```promql
   sum(rate(luminamind_response_quality_total{rating="bad"}[1h]))
   ```

---

**Monitoring Owner**: SRE Team  
**Docs**: https://prometheus.io/docs | https://grafana.com/docs  
**Support**: #luminamind-sre on Slack
