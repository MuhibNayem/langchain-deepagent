"""Tests for cost tracker."""
import pytest
from luminamind.cost.tracker import CostTracker


@pytest.fixture
def tracker(tmp_path):
    db = tmp_path / "costs.db"
    return CostTracker(db_path=db)


def test_record_usage(tracker):
    record = tracker.record(
        session_id="sess-1",
        thread_id="thread-1",
        model="gpt-4o-mini",
        input_tokens=1000,
        output_tokens=500,
    )
    assert record.cost_usd > 0
    assert record.total_tokens == 1500


def test_session_summary(tracker):
    tracker.record("sess-1", "thread-1", "gpt-4o-mini", 1000, 500)
    tracker.record("sess-1", "thread-1", "gpt-4o-mini", 2000, 1000)
    summary = tracker.session_summary("sess-1")
    assert summary["calls"] == 2
    assert summary["total_tokens"] == 4500
    assert summary["cost_usd"] > 0


def test_global_summary(tracker):
    tracker.record("sess-1", "t-1", "gpt-4o-mini", 1000, 500)
    tracker.record("sess-2", "t-2", "gpt-4o-mini", 2000, 1000)
    summary = tracker.global_summary()
    assert summary["calls"] == 2
    assert summary["total_tokens"] == 4500


def test_top_models(tracker):
    tracker.record("s", "t", "gpt-4o", 1000, 500)
    tracker.record("s", "t", "gpt-4o-mini", 2000, 1000)
    top = tracker.top_models()
    assert len(top) == 2
    assert top[0]["model"] == "gpt-4o"
