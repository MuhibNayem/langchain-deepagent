"""Tests for cost pricing database."""
from luminamind.cost.prices import get_pricing, list_priced_models


def test_get_pricing_known_model():
    p = get_pricing("gpt-4o")
    assert p is not None
    assert p.provider == "openai"
    assert p.input_per_1m > 0


def test_get_pricing_glm():
    p = get_pricing("glm-4.7-flash")
    assert p.provider == "z.ai"
    assert p.input_per_1m == 0.06


def test_get_pricing_kimi():
    p = get_pricing("kimi-k2.6")
    assert p.provider == "kimi"


def test_get_pricing_unknown_fallback():
    p = get_pricing("some-unknown-model-v123")
    assert p is not None
    assert p.input_per_1m > 0


def test_calculate_cost():
    p = get_pricing("gpt-4o-mini")
    cost = p.calculate(input_tokens=1_000_000, output_tokens=500_000)
    expected = 0.15 + (0.60 * 0.5)
    assert abs(cost - expected) < 0.001


def test_list_priced_models():
    models = list_priced_models()
    assert len(models) > 10
    providers = {m.provider for m in models}
    assert "z.ai" in providers
    assert "kimi" in providers
    assert "minimax" in providers
