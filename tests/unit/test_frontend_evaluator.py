"""Tests for FrontendEvaluator - visual quality scoring for frontend design artifacts.

GE-05: Frontend design evaluator produces actionable critique with visual quality scoring.
Covers: layout, typography, color, spacing, responsiveness.
"""
import pytest
from luminamind.evaluator.frontend import FrontendEvaluator


# Sample artifacts for testing
SAMPLE_HTML = """
<div class="container">
    <button class="btn-primary">Click me</button>
    <p style="font-size: 10px;">Small text</p>
</div>
"""

SAMPLE_CSS = """
.btn-primary {
    padding: 4px;
    background-color: #fff;
}
.container {
    display: flex;
    justify-content: center;
}
"""

SAMPLE_MIXED = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial; }
        .card { padding: 8px; margin: 16px; }
    </style>
</head>
<body>
    <header class="header">Title</header>
    <main class="content">
        <button class="btn">Action</button>
    </main>
</body>
</html>
"""


class TestFrontendEvaluator:
    """Test FrontendEvaluator visual quality scoring."""

    def test_visual_quality_scoring_layout(self):
        """FrontendEvaluator scores layout (0-100)."""
        evaluator = FrontendEvaluator()
        result = evaluator.evaluate(SAMPLE_HTML)
        assert "layout_score" in result
        assert 0 <= result["layout_score"] <= 100

    def test_visual_quality_scoring_typography(self):
        """FrontendEvaluator scores typography (0-100)."""
        evaluator = FrontendEvaluator()
        result = evaluator.evaluate(SAMPLE_HTML)
        assert "typography_score" in result
        assert 0 <= result["typography_score"] <= 100

    def test_visual_quality_scoring_color(self):
        """FrontendEvaluator scores color usage (0-100)."""
        evaluator = FrontendEvaluator()
        result = evaluator.evaluate(SAMPLE_HTML)
        assert "color_score" in result
        assert 0 <= result["color_score"] <= 100

    def test_visual_quality_scoring_spacing(self):
        """FrontendEvaluator scores spacing and alignment (0-100)."""
        evaluator = FrontendEvaluator()
        result = evaluator.evaluate(SAMPLE_HTML)
        assert "spacing_score" in result
        assert 0 <= result["spacing_score"] <= 100

    def test_visual_quality_scoring_responsiveness(self):
        """FrontendEvaluator scores responsiveness (0-100)."""
        evaluator = FrontendEvaluator()
        result = evaluator.evaluate(SAMPLE_HTML)
        assert "responsiveness_score" in result
        assert 0 <= result["responsiveness_score"] <= 100

    def test_visual_quality_overall_score(self):
        """Overall visual_quality_score is weighted average of dimension scores."""
        evaluator = FrontendEvaluator()
        result = evaluator.evaluate(SAMPLE_HTML)
        assert "visual_quality_score" in result
        assert 0 <= result["visual_quality_score"] <= 100

        # Verify it's approximately the weighted average
        expected = (
            result["layout_score"] * 0.25 +
            result["typography_score"] * 0.20 +
            result["color_score"] * 0.15 +
            result["spacing_score"] * 0.20 +
            result["responsiveness_score"] * 0.20
        )
        assert abs(result["visual_quality_score"] - expected) < 0.01

    def test_evaluate_returns_dict(self):
        """Evaluate returns dict with all required fields."""
        evaluator = FrontendEvaluator()
        result = evaluator.evaluate(SAMPLE_HTML)
        assert isinstance(result, dict)
        assert "visual_quality_score" in result
        assert "layout_score" in result
        assert "typography_score" in result
        assert "color_score" in result
        assert "spacing_score" in result
        assert "responsiveness_score" in result
        assert "issues" in result
        assert "strengths" in result
        assert "recommendations" in result


class TestActionableCritique:
    """Test actionable critique generation."""

    def test_critique_identifies_element_location(self):
        """Critique identifies specific element/location (e.g., 'button at line 42')."""
        evaluator = FrontendEvaluator()
        result = evaluator.evaluate(SAMPLE_HTML)
        issues = result.get("issues", [])

        # At least some issues should have location info
        if issues:
            has_location = any("location" in issue and issue["location"] for issue in issues)
            assert has_location, "Issues should identify specific element locations"

    def test_critique_provides_fix_suggestion(self):
        """Critique provides fix suggestion (e.g., 'increase padding to 16px')."""
        evaluator = FrontendEvaluator()
        result = evaluator.evaluate(SAMPLE_HTML)
        issues = result.get("issues", [])

        # Issues should have suggested_fix
        for issue in issues:
            assert "suggested_fix" in issue, f"Issue missing suggested_fix: {issue}"
            assert issue["suggested_fix"], f"suggested_fix should not be empty: {issue}"

    def test_critique_prioritizes_by_severity(self):
        """Critique prioritizes issues by severity (critical/major/minor)."""
        evaluator = FrontendEvaluator()
        result = evaluator.evaluate(SAMPLE_HTML)
        issues = result.get("issues", [])

        valid_severities = {"critical", "major", "minor"}
        for issue in issues:
            assert "severity" in issue, f"Issue missing severity: {issue}"
            assert issue["severity"] in valid_severities, f"Invalid severity: {issue['severity']}"

    def test_recommendations_map_to_issues(self):
        """Recommendations map 1:1 to issues."""
        evaluator = FrontendEvaluator()
        result = evaluator.evaluate(SAMPLE_HTML)
        recommendations = result.get("recommendations", [])

        for rec in recommendations:
            assert "action" in rec, f"Recommendation missing action: {rec}"
            assert "priority" in rec, f"Recommendation missing priority: {rec}"
            assert "expected_impact" in rec, f"Recommendation missing expected_impact: {rec}"
            assert rec["action"], f"Action should not be empty: {rec}"

    def test_critique_structure_complete(self):
        """Critique has location, description, severity, suggested_fix."""
        evaluator = FrontendEvaluator()
        result = evaluator.evaluate(SAMPLE_HTML)
        issues = result.get("issues", [])

        # Check issue structure
        for issue in issues:
            assert "type" in issue, f"Issue missing type: {issue}"
            assert "location" in issue, f"Issue missing location: {issue}"
            assert "description" in issue, f"Issue missing description: {issue}"
            assert "severity" in issue, f"Issue missing severity: {issue}"
            assert "suggested_fix" in issue, f"Issue missing suggested_fix: {issue}"


class TestIterationGuidance:
    """Test refine vs pivot iteration guidance."""

    def test_guidance_for_low_scores(self):
        """Iteration guidance indicates pivot when scores are very low."""
        evaluator = FrontendEvaluator()
        # Create a very poor quality artifact
        poor_artifacts = [
            "<div></div>",  # minimal
            "<p style='font-size:1px'>x</p>",  # tiny font
            "<button style='padding:0'>x</button>",  # no padding
        ]

        for artifact in poor_artifacts:
            result = evaluator.evaluate(artifact)
            # Should have low scores or specific guidance
            if result["visual_quality_score"] < 50:
                # Should have recommendations indicating major changes
                recommendations = result.get("recommendations", [])
                assert len(recommendations) > 0, f"Low score artifact should have recommendations: {artifact}"

    def test_guidance_for_medium_scores(self):
        """Iteration guidance indicates refine when scores are moderate."""
        evaluator = FrontendEvaluator()
        result = evaluator.evaluate(SAMPLE_MIXED)

        # Medium scores should suggest refine (incremental improvements)
        recommendations = result.get("recommendations", [])
        # There should be actionable recommendations for improvement
        if result["visual_quality_score"] < 80:
            assert len(recommendations) > 0, "Moderate score should have refinement recommendations"


class TestCriteriaWeights:
    """Test criteria weights from plan specification."""

    def test_weights_from_plan(self):
        """Criteria weights: design (0.3), originality (0.2), craft (0.25), functionality (0.25).

        For FrontendEvaluator visual scoring: layout (0.25), typography (0.20),
        color (0.15), spacing (0.20), responsiveness (0.20).
        """
        evaluator = FrontendEvaluator()
        result = evaluator.evaluate(SAMPLE_HTML)

        # Verify dimension scores exist
        assert "layout_score" in result
        assert "typography_score" in result
        assert "color_score" in result
        assert "spacing_score" in result
        assert "responsiveness_score" in result

        # Verify weighted average calculation
        weights = {
            "layout": 0.25,
            "typography": 0.20,
            "color": 0.15,
            "spacing": 0.20,
            "responsiveness": 0.20,
        }

        weighted_sum = sum(result[f"{dim}_score"] * w for dim, w in weights.items())
        assert abs(result["visual_quality_score"] - weighted_sum) < 0.01