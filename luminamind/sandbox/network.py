from dataclasses import dataclass
from typing import Optional

@dataclass
class EgressRule:
    """Rule for allowed outbound connections."""
    host: str  # IP or hostname pattern
    port: int | str  # port or "*"
    protocol: str = "tcp"  # tcp, udp
    comment: str = ""

class NetworkIsolation:
    """Network isolation configuration for sandbox."""
    
    def __init__(self):
        self._allow_all = False
        self._egress_rules: list[EgressRule] = []
        self._denied_hosts: set[str] = set()
    
    def allow_all(self) -> 'NetworkIsolation':
        """Allow all outbound connections (not recommended)."""
        self._allow_all = True
        return self
    
    def allow_egress(self, host: str, port: int | str = "*", protocol: str = "tcp") -> 'NetworkIsolation':
        """Add egress rule."""
        self._egress_rules.append(EgressRule(host=host, port=port, protocol=protocol))
        return self
    
    def deny_egress(self, host: str) -> 'NetworkIsolation':
        """Deny specific host."""
        self._denied_hosts.add(host)
        return self
    
    def is_allowed(self, host: str, port: int) -> bool:
        """Check if connection is allowed."""
        if self._allow_all:
            return host not in self._denied_hosts
        
        for rule in self._egress_rules:
            if self._matches_rule(host, port, rule):
                return True
        return False
    
    def _matches_rule(self, host: str, port: int, rule: EgressRule) -> bool:
        """Check if host:port matches rule."""
        import fnmatch
        if not fnmatch.fnmatch(host, rule.host):
            return False
        if rule.port != "*" and port != rule.port:
            return False
        return True
    
    def to_iptables(self) -> list[str]:
        """Generate iptables rules for this configuration."""
        pass
