"""Budget enforcement policies for enterprise cost control.

Supports:
- Hard caps (block when exceeded)
- Soft warnings (warn at threshold)
- Sliding window budgets (daily, weekly, monthly)
- Per-session and per-thread budgets
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from luminamind.cost.tracker import CostTracker, get_cost_tracker


class BudgetPolicyType(str, Enum):
    HARD_CAP = "hard_cap"
    SOFT_WARNING = "soft_warning"
    SLIDING_WINDOW = "sliding_window"


@dataclass
class BudgetPolicy:
    """A budget rule."""

    name: str
    policy_type: BudgetPolicyType
    limit_usd: float
    window_hours: float | None = None  # For sliding window
    scope: str = "global"  # global | session | thread | user
    scope_id: str | None = None
    warning_threshold: float = 0.8  # For soft warning

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "policy_type": self.policy_type.value,
            "limit_usd": self.limit_usd,
            "window_hours": self.window_hours,
            "scope": self.scope,
            "scope_id": self.scope_id,
            "warning_threshold": self.warning_threshold,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BudgetPolicy":
        return cls(
            name=data["name"],
            policy_type=BudgetPolicyType(data["policy_type"]),
            limit_usd=data["limit_usd"],
            window_hours=data.get("window_hours"),
            scope=data.get("scope", "global"),
            scope_id=data.get("scope_id"),
            warning_threshold=data.get("warning_threshold", 0.8),
        )


class BudgetExceededError(Exception):
    """Raised when a hard-cap budget is exceeded."""

    def __init__(self, policy: BudgetPolicy, current: float) -> None:
        super().__init__(
            f"Budget '{policy.name}' exceeded: ${current:.4f} / ${policy.limit_usd:.4f} "
            f"(scope={policy.scope}, id={policy.scope_id})"
        )
        self.policy = policy
        self.current = current


class BudgetWarning:
    """A soft warning about approaching budget limits."""

    def __init__(self, policy: BudgetPolicy, current: float, ratio: float) -> None:
        self.policy = policy
        self.current = current
        self.ratio = ratio
        self.message = (
            f"Warning: Budget '{policy.name}' at {ratio:.1%} "
            f"(${current:.4f} / ${policy.limit_usd:.4f})"
        )


class BudgetEnforcer:
    """Enforces budget policies against the cost tracker."""

    CONFIG_PATH = Path.home() / ".luminamind" / "budgets.json"

    def __init__(self, tracker: CostTracker | None = None) -> None:
        self.tracker = tracker or get_cost_tracker()
        self._policies: list[BudgetPolicy] = []
        self._load_policies()

    def _load_policies(self) -> None:
        if self.CONFIG_PATH.exists():
            try:
                data = json.loads(self.CONFIG_PATH.read_text(encoding="utf-8"))
                self._policies = [BudgetPolicy.from_dict(p) for p in data.get("policies", [])]
            except Exception:
                self._policies = []
        else:
            self._policies = self._default_policies()
            self._save_policies()

    def _save_policies(self) -> None:
        self.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {"policies": [p.to_dict() for p in self._policies]}
        self.CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _default_policies(self) -> list[BudgetPolicy]:
        return [
            BudgetPolicy(
                name="default_session_cap",
                policy_type=BudgetPolicyType.SOFT_WARNING,
                limit_usd=10.0,
                scope="session",
                warning_threshold=0.9,
            ),
            BudgetPolicy(
                name="default_global_daily",
                policy_type=BudgetPolicyType.HARD_CAP,
                limit_usd=50.0,
                window_hours=24,
                scope="global",
            ),
        ]

    def add_policy(self, policy: BudgetPolicy) -> None:
        self._policies.append(policy)
        self._save_policies()

    def remove_policy(self, name: str) -> bool:
        before = len(self._policies)
        self._policies = [p for p in self._policies if p.name != name]
        if len(self._policies) < before:
            self._save_policies()
            return True
        return False

    def list_policies(self) -> list[BudgetPolicy]:
        return list(self._policies)

    def _current_spend(self, policy: BudgetPolicy, session_id: str | None = None, thread_id: str | None = None) -> float:
        if policy.scope == "global":
            since = None
            if policy.window_hours:
                since = (datetime.now(timezone.utc) - timedelta(hours=policy.window_hours)).isoformat()
            return self.tracker.global_summary(since=since)["cost_usd"]
        elif policy.scope == "session" and session_id:
            return self.tracker.session_summary(session_id)["cost_usd"]
        elif policy.scope == "thread" and thread_id:
            return self.tracker.thread_summary(thread_id)["cost_usd"]
        return 0.0

    def check(
        self,
        session_id: str | None = None,
        thread_id: str | None = None,
    ) -> tuple[list[BudgetExceededError], list[BudgetWarning]]:
        """Check all policies and return (errors, warnings)."""
        errors: list[BudgetExceededError] = []
        warnings: list[BudgetWarning] = []
        for policy in self._policies:
            current = self._current_spend(policy, session_id, thread_id)
            if policy.policy_type == BudgetPolicyType.HARD_CAP:
                if current >= policy.limit_usd:
                    errors.append(BudgetExceededError(policy, current))
            elif policy.policy_type == BudgetPolicyType.SOFT_WARNING:
                ratio = current / policy.limit_usd if policy.limit_usd > 0 else 0.0
                if ratio >= policy.warning_threshold:
                    warnings.append(BudgetWarning(policy, current, ratio))
            elif policy.policy_type == BudgetPolicyType.SLIDING_WINDOW:
                ratio = current / policy.limit_usd if policy.limit_usd > 0 else 0.0
                if ratio >= 1.0:
                    errors.append(BudgetExceededError(policy, current))
                elif ratio >= policy.warning_threshold:
                    warnings.append(BudgetWarning(policy, current, ratio))
        return errors, warnings

    def enforce(
        self,
        session_id: str | None = None,
        thread_id: str | None = None,
    ) -> list[BudgetWarning]:
        """Enforce budgets. Raises BudgetExceededError on hard cap violation."""
        errors, warnings = self.check(session_id, thread_id)
        if errors:
            raise errors[0]
        return warnings


# Singleton
_enforcer: BudgetEnforcer | None = None


def get_budget_enforcer() -> BudgetEnforcer:
    global _enforcer
    if _enforcer is None:
        _enforcer = BudgetEnforcer()
    return _enforcer
