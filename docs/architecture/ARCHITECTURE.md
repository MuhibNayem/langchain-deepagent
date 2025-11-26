# System Architecture
## LuminaMind Deep Agent Framework

> **Status**: Production Readiness Planning  
> **Last Updated**: November 26, 2025  
> **Version**: 0.0.1.1.3

---

## Overview

LuminaMind is a multi-agent autonomous AI system built on LangGraph, designed for code analysis, web research, and software development automation.

### Architecture Principles

1. **Modularity**: Pluggable tool system
2. **Resilience**: Circuit breakers, retries, graceful degradation
3. **Observability**: Comprehensive logging, metrics, tracing
4. **Scalability**: Horizontal scaling via Kubernetes
5. **Security**: Defense in depth, least privilege

---

## High-Level Architecture

```mermaid
graph TB
    User[User/CLI] --> |HTTP/gRPC| LB[Load Balancer]
    LB --> |Route| Pod1[LuminaMind Pod 1]
    LB --> |Route| Pod2[LuminaMind Pod 2]
    LB --> |Route| Pod3[LuminaMind Pod 3]
    
    Pod1 --> |Query| LLM[LLM Provider<br/>GLM-4.5 / GPT-4]
    Pod2 --> |Query| LLM
    Pod3 --> |Query| LLM
    
    Pod1 --> |Read/Write| Redis[Redis Cluster<br/>3 Nodes]
    Pod2 --> |Read/Write| Redis
    Pod3 --> |Read/Write| Redis
    
    Pod1 --> |Cache| Cache[Redis Cache]
    Pod2 --> |Cache| Cache
    Pod3 --> |Cache| Cache
    
    Pod1 --> |Metrics| Prom[Prometheus]
    Pod2 --> |Metrics| Prom
    Pod3 --> |Metrics| Prom
    
    Prom --> |Visualize| Graf[Grafana]
    
    Pod1 --> |Logs| Loki[Loki/ELK]
    Pod2 --> |Logs| Loki
    Pod3 --> |Logs| Loki
    
    Pod1 --> |Search| WebAPI[Web APIs<br/>Serper, Google]
    Pod2 --> |Search| WebAPI
    Pod3 --> |Search| WebAPI
    
    Redis --> |Backup| S3[S3 Storage]
    
    style LLM fill:#f9f,stroke:#333
    style Redis fill:#ff9,stroke:#333
    style Pod1 fill:#9f9,stroke:#333
    style Pod2 fill:#9f9,stroke:#333
    style Pod3 fill:#9f9,stroke:#333
```

---

## Component Architecture

### 1. Agent Core

```mermaid
graph LR
    UI[User Input] --> Main[Main Agent]
    Main --> |Delegate| WebRes[Web Researcher<br/>Subagent]
    Main --> |Delegate| CodeExec[Code Executor<br/>Subagent]
    Main --> |Delegate| Greet[Greeting<br/>Subagent]
    
    WebRes --> |Uses| WebTools[Web Tools<br/>web_search<br/>web_crawl<br/>weather]
    CodeExec --> |Uses| CodeTools[Code Tools<br/>shell<br/>file_ops<br/>grep<br/>tree]
    
    Main --> |State| Checkpoint[Checkpointer<br/>Redis/File]
    Main --> |Query| LLM[LLM Provider]
    
    style Main fill:#9cf,stroke:#333,stroke-width:3px
    style WebRes fill:#fcf,stroke:#333
    style CodeExec fill:#cff,stroke:#333
```

**Main Agent** (`luminamind/deep_agent.py`):
- Orchestrates subagents
- Manages conversation state
- Handles human-in-the-loop approvals
- Routes tasks to specialized subagents

**Subagents**:
1. **Web Researcher**: Deep research, fact gathering, web search
2. **Code Executor**: File operations, shell commands, code analysis
3. **Greeting Responder**: Casual conversation, greetings

### 2. Tool Ecosystem

```mermaid
graph TB
    subgraph "File Tools"
    Read[read_file]
    Write[write_file]
    Copy[copy_file]
    Delete[delete_file]
    List[list_directory]
    Search[file_search]
    end
    
    subgraph "Web Tools"
    WebS[web_search]
    WebC[web_crawl]
    Weather[get_weather]
    Fetch[fetch_as_markdown]
    end
    
    subgraph "Code Tools"
    Shell[shell]
    Grep[grep_search]
    Tree[tree_view]
   MultiReplace[multi_replace_in_file]
    Patch[apply_patch]
    end
    
    subgraph "System Tools"
    OSInfo[os_info]
    Safety[safety checks]
    end
    
    Agent[Main Agent] --> File Tools
    Agent --> Web Tools
    Agent --> Code Tools
    Agent --> System Tools
```

**Tool Registry** (`luminamind/py_tools/registry.py`):
```python
PY_TOOL_REGISTRY = {
    "os_info": os_info,
    "shell": shell,
    "web_search": web_search,
    "web_crawl": web_crawl,
    "get_weather": get_weather,
    # ... more tools
}
```

### 3. State Management

```mermaid
sequenceDiagram
    participant User
    participant Agent
    participant Checkpointer
    participant Redis
    
    User->>Agent: Send message (thread_id)
    Agent->>Checkpointer: Load state (thread_id)
    Checkpointer->>Redis: GET checkpoints:{thread_id}
    Redis-->>Checkpointer: Previous state
    Checkpointer-->>Agent: Loaded state
    
    Agent->>Agent: Process with LLM
    Agent->>Agent: Execute tools
    
    Agent->>Checkpointer: Save state
    Checkpointer->>Redis: SET checkpoints:{thread_id}
    Redis-->>Checkpointer: OK
    
    Agent-->>User: Response
```

**Checkpointer** (`luminamind/config/checkpointer.py`):
- **Primary**: `RedisBackedMemorySaver` (production)
- **Fallback**: `FileBackedMemorySaver` (development)
- **Interface**: LangGraph `MemorySaver`

**State Includes**:
- Message history
- Tool execution results
- Pending approvals
- Agent metadata

### 4. LLM Provider Abstraction

```python
def get_llm():
    provider = os.environ.get("LLM_PROVIDER", "openai")
    
    if provider == "ollama":
        return ChatOllama(
            model=os.environ.get("OLLAMA_MODEL", "qwen3:latest"),
            base_url=os.environ.get("OLLAMA_BASE_URL"),
            temperature=0.7,
            streaming=True
        )
    
    return ChatOpenAI(
        temperature=0.7,
        model="glm-4.5-flash",
        openai_api_key=os.environ.get("GLM_API_KEY"),
        openai_api_base="https://api.z.ai/api/paas/v4/",
        streaming=True
    )
```

**Supported Providers**:
- **OpenAI-compatible**: GLM-4.5-Flash (default)
- **Ollama**: Local models (qwen3, llama3, etc.)

---

## Data Flow

### Request Processing Flow

```mermaid
flowchart TD
    Start([User Input]) --> Parse[Parse Command]
    Parse --> LoadState[Load Conversation State<br/>from Checkpointer]
    
    LoadState --> Planning[LLM: Planning Phase]
    Planning --> |Creates TODO| SubagentSelect{Select Subagent?}
    
    SubagentSelect --> |Yes| Delegate[Delegate to Subagent]
    SubagentSelect --> |No| ToolSelect[Select Tools]
    
    Delegate --> SubagentExec[Subagent Execution]
    SubagentExec --> ToolExec[Tool Execution]
    
    ToolSelect --> HITL{Requires<br/>Approval?}
    
    HITL --> |Yes| Prompt[Prompt User]
    Prompt --> Approved{Approved?}
    Approved --> |No| Reject[Reject & Continue]
    Approved --> |Yes| ToolExec
    
    HITL --> |No| ToolExec
    
    ToolExec --> LLMReflect[LLM: Reflect on Results]
    LLMReflect --> Complete{Task<br/>Complete?}
    
    Complete --> |No| Planning
    Complete --> |Yes| SaveState[Save State to Checkpointer]
    
    SaveState --> Response([Return Response])
    
    Reject --> Planning
    
    style Planning fill:#9cf,stroke:#333
    style ToolExec fill:#fcf,stroke:#333
    style SaveState fill:#ff9,stroke:#333
```

### Tool Execution with Observability

```mermaid
sequenceDiagram
    participant Agent
    participant Logger
    participant Metrics
    participant Tool
    participant Cache
    participant External
    
    Agent->>Logger: Log tool_start
    Agent->>Metrics: Increment tool_calls_total
    Agent->>Metrics: Start duration timer
    
    Agent->>Cache: Check cache
    alt Cache Hit
        Cache-->>Agent: Cached result
        Agent->>Metrics: Increment cache_hits
    else Cache Miss
        Agent->>Tool: Execute
        Tool->>External: API call / Command
        External-->>Tool: Result
        Tool-->>Agent: Result
        Agent->>Cache: Store result
    end
    
    Agent->>Metrics: Record duration
    Agent->>Logger: Log tool_end
    Agent-->>Agent: Return to main flow
```

---

## Production Architecture

### Kubernetes Deployment

```mermaid
graph TB
    subgraph "Ingress Layer"
    Ingress[Ingress Controller<br/>NGINX/ALB]
    end
    
    subgraph "Application Layer"
    SVC[Service<br/>luminamind-service]
    SVC --> Pod1[Pod 1<br/>luminamind]
    SVC --> Pod2[Pod 2<br/>luminamind]
    SVC --> Pod3[Pod 3<br/>luminamind]
    SVC --> PodN[Pod N<br/>...auto-scaled]
    end
    
    subgraph "Data Layer"
    Redis[Redis StatefulSet<br/>3 Masters + 3 Replicas]
    S3[S3 Backups<br/>Daily snapshots]
    end
    
    subgraph "Observability"
    Prom[Prometheus<br/>Metrics]
    Loki[Loki<br/>Logs]
    Jaeger[Jaeger<br/>Traces]
    Graf[Grafana<br/>Dashboards]
    end
    
    subgraph "External"
    Vault[HashiCorp Vault<br/>Secrets]
    LLM[LLM APIs<br/>GLM/GPT]
    WebAPIs[Web APIs<br/>Serper/Google]
    end
    
    Ingress --> SVC
    
    Pod1 --> Redis
    Pod2 --> Redis
    Pod3 --> Redis
    PodN --> Redis
    
    Pod1 --> Prom
    Pod2 --> Prom
    Pod3 --> Prom
    PodN --> Prom
    
    Pod1 --> Loki
    Pod2 --> Loki
    Pod3 --> Loki
    PodN --> Loki
    
    Redis --> S3
    
    Pod1 -.->|Secrets| Vault
    Pod1 -.->|Query| LLM
    Pod1 -.->|Search| WebAPIs
    
    Prom --> Graf
    Loki --> Graf
    Jaeger --> Graf
    
    style SVC fill:#9cf,stroke:#333,stroke-width:2px
    style Redis fill:#ff9,stroke:#333,stroke-width:2px
    style Vault fill:#f99,stroke:#333,stroke-width:2px
```

### Resource Allocation

**Per Pod**:
- **CPU**: 500m request, 2000m limit
- **Memory**: 512Mi request, 2Gi limit
- **Replicas**: Min 3, Max 10
- **Auto-scale trigger**: CPU >70% or Memory >80%

**Redis Cluster**:
- **Nodes**: 3 masters + 3 replicas
- **Memory**: 4Gi per node
- **Persistence**: AOF + RDB snapshots
- **Backup**: Daily to S3

---

## Security Architecture

### Defense in Depth

```mermaid
graph TB
    subgraph "Perimeter Security"
    WAF[Web Application Firewall]
    RateLimit[Rate Limiter]
    end
    
    subgraph "Network Security"
    TLS[TLS/SSL Encryption]
    NetPol[Network Policies]
    end
    
    subgraph "Application Security"
    InputVal[Input Validation]
    Sanitize[Command Sanitization]
    AuthZ[Authorization]
    end
    
    subgraph "Data Security"
    SecMgr[Secrets Manager<br/>Vault]
    Encrypt[Encryption at Rest]
    end
    
    subgraph "Monitoring"
    AuditLog[Audit Logging]
    SIEM[Security Monitoring]
    Alerts[Security Alerts]
    end
    
    User[User Request] --> WAF
    WAF --> RateLimit
    RateLimit --> TLS
    TLS --> NetPol
    NetPol --> InputVal
    InputVal --> Sanitize
    Sanitize --> AuthZ
    
    AuthZ --> SecMgr
    AuthZ --> Encrypt
    
    InputVal -.->|Log| AuditLog
    Sanitize -.->|Log| AuditLog
    AuthZ -.->|Log| AuditLog
    
    AuditLog --> SIEM
    SIEM --> Alerts
    
    style InputVal fill:#f99,stroke:#333,stroke-width:2px
    style SecMgr fill:#f99,stroke:#333,stroke-width:2px
```

### Security Controls

1. **Input Validation**:
   - Pydantic schemas for all inputs
   - Command whitelist for `shell` tool
   - Path validation for file operations

2. **Secrets Management**:
   - HashiCorp Vault for API keys
   - Kubernetes secrets for configs
   - No secrets in code or logs

3. **Network Security**:
   - TLS 1.3 for all external communication
   - Network policies in Kubernetes
   - Private subnets for data layer

4. **Audit Logging**:
   - All tool executions logged
   - User actions tracked
   - Security events alerted

---

## Observability Architecture

### The Three Pillars

```mermaid
graph LR
    subgraph "Logs"
    App1[App Logs] --> Loki[Loki/ELK]
    App2[System Logs] --> Loki
    App3[Audit Logs] --> Loki
    end
    
    subgraph "Metrics"
    Prom[Prometheus]
    App1 --> |/metrics| Prom
    Redis[Redis] --> |Exporter| Prom
    K8s[Kubernetes] --> |kube-state| Prom
    end
    
    subgraph "Traces"
    App1 --> |OTLP| Jaeger[Jaeger/Tempo]
    end
    
    Loki --> Grafana[Grafana<br/>Unified View]
    Prom --> Grafana
    Jaeger --> Grafana
    
    Grafana --> Alerts[Alertmanager]
    Alerts --> PagerDuty[PagerDuty]
    Alerts --> Slack[Slack]
    
    style Grafana fill:#9cf,stroke:#333,stroke-width:3px
```

### Key Dashboards

1. **Application Health**
   - Request rate, error rate, latency (RED metrics)
   - Tool usage distribution
   - LLM token consumption
   - Cache hit rate

2. **Infrastructure Health**
   - Pod CPU/memory usage
   - Redis performance
   - Network I/O
   - Disk usage

3. **Business Metrics**
   - Accuracy rate
   - User satisfaction
   - Cost per request
   - Active users

### Alert Rules

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| High Error Rate | >1% | Critical | Page on-call |
| Slow Response | P95 >10s | Warning | Investigate |
| Pod Crash Loop | >3 restarts/10min | Critical | Page on-call |
| Redis Down | Unavailable | Critical | Auto-failover + page |
| Low Accuracy | <90% | Warning | QA review |
| High Token Usage | >2x baseline | Info | Cost alert |

---

## Scalability

### Horizontal Scaling

**Auto-scaling Triggers**:
```yaml
metrics:
- type: Resource
  resource:
    name: cpu
    target:
      averageUtilization: 70
- type: Resource
  resource:
    name: memory
    target:
      averageUtilization: 80
- type: Pods
  pods:
    metric:
      name: request_rate
    target:
      type: AverageValue
      averageValue: "100"  # RPS per pod
```

**Scale Strategy**:
- **Min replicas**: 3 (HA requirement)
- **Max replicas**: 10 (cost ceiling)
- **Scale up**: Add pod when CPU >70% for 2 minutes
- **Scale down**: Remove pod when CPU <30% for 5 minutes

### Performance Optimization

**Caching Strategy**:
```mermaid
graph LR
    Request[Request] --> CacheCheck{Cache<br/>Hit?}
    CacheCheck -->|Yes| Return[Return Cached<br/>60% of requests]
    CacheCheck -->|No| Compute[Compute<br/>40% of requests]
    Compute --> Store[Store in Cache<br/>TTL: 1h]
    Store --> Return
    
    style CacheCheck fill:#9f9,stroke:#333
    style Return fill:#9cf,stroke:#333
```

**Expected Performance**:
- **Without cache**: 100% requests hit LLM/tools
- **With cache (60% hit rate)**: 40% requests hit LLM/tools
- **Cost savings**: ~50% on LLM API costs
- **Latency improvement**: P95 from ~8s to ~3s

---

## Disaster Recovery

### Backup Strategy

```mermaid
graph LR
    Redis[Redis AOF] -->|Real-time| AOF[AOF File]
    Redis -->|Hourly| RDB[RDB Snapshot]
    
    RDB -->|Daily| S3[S3 Backup<br/>30-day retention]
    AOF -->|On-change| S3
    
    S3 -->|Weekly| Glacier[Glacier<br/>1-year archive]
    
    style S3 fill:#9cf,stroke:#333,stroke-width:2px
```

**Backup Schedule**:
- **Real-time**: AOF (Append-Only File)
- **Hourly**: RDB snapshots
- **Daily**: S3 upload (retain 30 days)
- **Weekly**: Glacier archive (retain 1 year)

**Recovery Procedures**:

1. **Pod Failure** (RTO: <30s)
   - Kubernetes auto-restarts
   - Load balancer routes to healthy pods

2. **Redis Failure** (RTO: <2min)
   - Redis Sentinel promotes replica to master
   - Pods reconnect automatically

3. **Complete Cluster Loss** (RTO: <30min)
   - Restore from latest S3 backup
   - Recreate Redis cluster
   - Redeploy pods

### Recovery Targets

| Scenario | RTO | RPO | Procedure |
|----------|-----|-----|-----------|
| Pod crash | <30s | 0 | Auto-restart |
| Redis node down | <2min | <1s (AOF) | Sentinel failover |
| Availability zone | <5min | <1min | Cross-AZ replica |
| Region failure | <30min | <1hour | S3 restore |

---

## Technology Stack

### Core Framework
- **Agent**: LangGraph 1.0.3
- **LLM Integration**: LangChain 1.0.8
- **LLM Providers**: OpenAI-compatible (GLM-4.5), Ollama

### Infrastructure
- **Container Orchestration**: Kubernetes
- **State Management**: Redis 5.0.4
- **Secrets**: HashiCorp Vault
- **Load Balancing**: Kubernetes Service / Ingress

### Observability
- **Logging**: Structlog + Loki/ELK
- **Metrics**: Prometheus + Grafana
- **Tracing**: OpenTelemetry + Jaeger
- **Alerting**: Alertmanager + PagerDuty

### Development
- **Language**: Python 3.12
- **Package Manager**: Poetry
- **Testing**: Pytest
- **CI/CD**: GitHub Actions

---

## Future Enhancements

### Phase 1 (Q1 2026)
- [ ] Multi-tenancy support
- [ ] Advanced caching (semantic similarity)
- [ ] Fine-tuned domain models

### Phase 2 (Q2 2026)
- [ ] Multi-region deployment
- [ ] GraphQL API
- [ ] Real-time collaboration

### Phase 3 (Q3 2026)
- [ ] Plugin marketplace
- [ ] Advanced analytics
- [ ] Custom agent training

---

**Architecture Owner**: Engineering Lead  
**Last Review**: November 26, 2025  
**Next Review**: Quarterly  
**RFC Process**: [Submit architecture proposals](https://github.com/yourorg/luminamind/rfcs)
