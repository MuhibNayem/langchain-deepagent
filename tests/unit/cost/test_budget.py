"""Tests for budget enforcement."""
import pytest
from luminamind.cost.budget import (
    BudgetEnforcer,
    BudgetExceededError,
    BudgetPolicy,
    BudgetPolicyType,
)
from luminamind.cost.tracker import CostTracker


@pytest.fixture
def enforcer(tmp_path):
    db = tmp_path / "costs.db"
    tracker = CostTracker(db_path=db)
    return BudgetEnforcer(tracker=tracker)


def test_hard_cap(enforcer):
    # Clear default policies first
    for p in list(enforcer.list_policies()):
        enforcer.remove_policy(p.name)

    enforcer.add_policy(
        BudgetPolicy(
            name="test_cap",
            policy_type=BudgetPolicyType.HARD_CAP,
            limit_usd=1.0,
            scope="global",
        )
    )
    # Should pass when under budget
    errors, warnings = enforcer.check()
    assert len(errors) == 0

    # Simulate spend over budget
    enforcer.tracker.record("s", "t", "gpt-4o", 1_000_000, 0)
    with pytest.raises(BudgetExceededError):
        enforcer.enforce()


def test_soft_warning(enforcer):
    # Clear default policies first
    for p in list(enforcer.list_policies()):
        enforcer.remove_policy(p.name)

    enforcer.add_policy(
        BudgetPolicy(
            name="test_warn",
            policy_type=BudgetPolicyType.SOFT_WARNING,
            limit_usd=1.0,
            scope="global",
            warning_threshold=0.5,
        )
    )
    # No warning initially
    errors, warnings = enforcer.check()
    assert len(warnings) == 0

    # Spend enough to trigger warning
    enforcer.tracker.record("s", "t", "gpt-4o", 500_000, 0)
    errors, warnings = enforcer.check()
    assert len(warnings) == 1
    assert "test_warn" in warnings[0].message
