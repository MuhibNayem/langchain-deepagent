"""Tests for CodeEvaluator - RED phase for correctness and maintainability."""
from __future__ import annotations

import pytest


CORRECT_CODE = "def add(a, b): return a + b"
BUGGY_CODE = "def divide(a, b): return a / b  # Missing zero check"
COMPLEX_CODE = """
for i in range(n):
    for j in range(n):
        for k in range(n):
            print(i, j, k)
"""
INSECURE_CODE = "import os; os.system('rm -rf ' + user_input)"


class TestCodeEvaluatorCorrectness:
    """Tests for correctness scoring."""

    def test_correctness_scoring_detects_bugs(self):
        """Test: Correctness scoring detects bug presence."""
        from luminamind.evaluator.code import CodeEvaluator

        evaluator = CodeEvaluator()
        result = evaluator.evaluate(BUGGY_CODE)
        assert result["correctness_score"] < 100, "Correctness score should be reduced for buggy code"
        assert len(result["issues"]) > 0, "Should detect issues in buggy code"

    def test_correctness_scoring_clean_code(self):
        """Test: Correctness scoring awards high score to clean code."""
        from luminamind.evaluator.code import CodeEvaluator

        evaluator = CodeEvaluator()
        result = evaluator.evaluate(CORRECT_CODE)
        assert result["correctness_score"] >= 80, "Clean code should score well on correctness"

    def test_correctness_detects_infinite_loops(self):
        """Test: Correctness detects infinite loops (while True without break)."""
        from luminamind.evaluator.code import CodeEvaluator

        infinite_loop = """
while True:
    print("looping")
"""
        evaluator = CodeEvaluator()
        result = evaluator.evaluate(infinite_loop)
        assert result["correctness_score"] < 100, "Infinite loop should reduce correctness score"
        assert any("loop" in str(i).lower() for i in result["issues"]), "Should flag loop issue"

    def test_correctness_detects_null_dereferences(self):
        """Test: Correctness detects null dereferences."""
        from luminamind.evaluator.code import CodeEvaluator

        null_code = """
result = None
print(result.value)
"""
        evaluator = CodeEvaluator()
        result = evaluator.evaluate(null_code)
        assert result["correctness_score"] < 100, "Null dereference should reduce correctness score"

    def test_correctness_detects_division_by_zero_risk(self):
        """Test: Correctness detects division without zero check."""
        from luminamind.evaluator.code import CodeEvaluator

        evaluator = CodeEvaluator()
        result = evaluator.evaluate(BUGGY_CODE)
        assert result["correctness_score"] < 100, "Division without zero check should reduce score"


class TestCodeEvaluatorMaintainability:
    """Tests for maintainability scoring."""

    def test_maintainability_scoring(self):
        """Test: Maintainability scores complexity, coupling, naming."""
        from luminamind.evaluator.code import CodeEvaluator

        evaluator = CodeEvaluator()
        result = evaluator.evaluate(COMPLEX_CODE)
        assert result["maintainability_score"] < 90, "Complex code should score low on maintainability"

    def test_maintainability_detects_high_cyclomatic_complexity(self):
        """Test: Maintainability detects high cyclomatic complexity."""
        from luminamind.evaluator.code import CodeEvaluator

        high_complexity = """
if a:
    if b:
        if c:
            if d:
                if e:
                    pass
"""
        evaluator = CodeEvaluator()
        result = evaluator.evaluate(high_complexity)
        assert result["maintainability_score"] < 70, "High complexity should reduce maintainability score"

    def test_maintainability_detects_long_functions(self):
        """Test: Maintainability detects long functions (>50 lines)."""
        from luminamind.evaluator.code import CodeEvaluator

        long_func = """
def process_data(data):
    result = []
    for item in data:
        result.append(item * 2)
    for item in result:
        if item > 0:
            result.remove(item)
    return result
"""
        evaluator = CodeEvaluator()
        result = evaluator.evaluate(long_func)
        # Should detect the function is long
        assert result["maintainability_score"] < 100, "Long function should reduce maintainability score"

    def test_maintainability_detects_deep_nesting(self):
        """Test: Maintainability detects deep nesting (>4 levels)."""
        from luminamind.evaluator.code import CodeEvaluator

        deeply_nested = """
for i in range(10):
    for j in range(10):
        for k in range(10):
            for l in range(10):
                for m in range(10):
                    x = i + j + k + l + m
"""
        evaluator = CodeEvaluator()
        result = evaluator.evaluate(deeply_nested)
        assert result["maintainability_score"] < 70, "Deep nesting should reduce maintainability score"

    def test_maintainability_detects_magic_numbers(self):
        """Test: Maintainability detects magic numbers."""
        from luminamind.evaluator.code import CodeEvaluator

        magic_numbers = """
value = 42
if value == 42:
    print("magic")
"""
        evaluator = CodeEvaluator()
        result = evaluator.evaluate(magic_numbers)
        # Magic numbers should be flagged
        assert result["maintainability_score"] < 100, "Magic numbers should reduce maintainability score"


class TestCodeEvaluatorPerformance:
    """Tests for performance scoring."""

    def test_performance_scoring(self):
        """Test: Performance scores algorithm complexity, resource usage."""
        from luminamind.evaluator.code import CodeEvaluator

        evaluator = CodeEvaluator()
        result = evaluator.evaluate(COMPLEX_CODE)
        assert result["performance_score"] <= 70, "Complex code should score low on performance"

    def test_performance_detects_quadratic_complexity(self):
        """Test: Performance detects O(n²) nested loops."""
        from luminamind.evaluator.code import CodeEvaluator

        evaluator = CodeEvaluator()
        result = evaluator.evaluate(COMPLEX_CODE)
        assert result["performance_score"] <= 70, "O(n²) complexity should reduce performance score"
        assert any("quadratic" in str(i).lower() or "nested" in str(i).lower()
                  for i in result["issues"]), "Should flag nested loop issue"

    def test_performance_detects_unbounded_operations(self):
        """Test: Performance detects unbounded operations."""
        from luminamind.evaluator.code import CodeEvaluator

        unbounded = """
results = []
for item in large_dataset:
    results.append(process(item))
"""
        evaluator = CodeEvaluator()
        result = evaluator.evaluate(unbounded)
        # Should flag unbounded operation
        assert result["performance_score"] < 100, "Unbounded operations should reduce performance score"

    def test_performance_scoring_clean_code(self):
        """Test: Performance scores clean code highly."""
        from luminamind.evaluator.code import CodeEvaluator

        evaluator = CodeEvaluator()
        result = evaluator.evaluate(CORRECT_CODE)
        assert result["performance_score"] >= 80, "Clean code should score well on performance"


class TestCodeEvaluatorSecurity:
    """Tests for security scoring."""

    def test_security_scoring(self):
        """Test: Security scores OWASP Top 10, injection, auth issues."""
        from luminamind.evaluator.code import CodeEvaluator

        evaluator = CodeEvaluator()
        result = evaluator.evaluate(INSECURE_CODE)
        assert result["security_score"] < 90, "Insecure code should score low on security"

    def test_security_detects_shell_injection(self):
        """Test: Security detects shell injection vulnerability."""
        from luminamind.evaluator.code import CodeEvaluator

        evaluator = CodeEvaluator()
        result = evaluator.evaluate(INSECURE_CODE)
        assert result["security_score"] < 90, "Shell injection should reduce security score"
        assert any("shell" in str(i).lower() for i in result["issues"]), "Should flag shell injection"

    def test_security_detects_sql_injection(self):
        """Test: Security detects SQL injection vulnerability."""
        from luminamind.evaluator.code import CodeEvaluator

        sql_injection = """
query = "SELECT * FROM users WHERE id = " + user_id
cursor.execute(query)
"""
        evaluator = CodeEvaluator()
        result = evaluator.evaluate(sql_injection)
        assert result["security_score"] < 90, "SQL injection should reduce security score"

    def test_security_detects_hardcoded_secrets(self):
        """Test: Security detects hardcoded API keys and secrets."""
        from luminamind.evaluator.code import CodeEvaluator

        with_secrets = '''
api_key = "sk-1234567890abcdef"
password = "secret123"
'''
        evaluator = CodeEvaluator()
        result = evaluator.evaluate(with_secrets)
        assert result["security_score"] < 90, "Hardcoded secrets should reduce security score"

    def test_security_scoring_clean_code(self):
        """Test: Security scores clean code highly."""
        from luminamind.evaluator.code import CodeEvaluator

        evaluator = CodeEvaluator()
        result = evaluator.evaluate(CORRECT_CODE)
        assert result["security_score"] >= 80, "Clean code should score well on security"


class TestCodeEvaluatorOverall:
    """Tests for overall score calculation."""

    def test_overall_score_calculation(self):
        """Test: Overall score is weighted average of all dimensions."""
        from luminamind.evaluator.code import CodeEvaluator

        evaluator = CodeEvaluator()
        result = evaluator.evaluate(CORRECT_CODE)
        assert 0 <= result["overall_score"] <= 100, "Overall score should be 0-100"
        # Weighted average check
        expected = (
            result["correctness_score"] * 0.30 +
            result["maintainability_score"] * 0.25 +
            result["performance_score"] * 0.20 +
            result["security_score"] * 0.25
        )
        assert abs(result["overall_score"] - expected) < 0.01, "Overall should be weighted average"

    def test_overall_score_with_issues(self):
        """Test: Overall score reflects issues in all dimensions."""
        from luminamind.evaluator.code import CodeEvaluator

        evaluator = CodeEvaluator()
        result = evaluator.evaluate(COMPLEX_CODE)
        # With nested loops, both perf and maint should be reduced
        assert result["overall_score"] < 90, "Code with issues should have reduced overall score"

    def test_issues_include_severity_and_remediation(self):
        """Test: Issues include severity and remediation guidance."""
        from luminamind.evaluator.code import CodeEvaluator

        evaluator = CodeEvaluator()
        result = evaluator.evaluate(INSECURE_CODE)
        # Find security issues
        security_issues = [i for i in result["issues"] if i.get("type") == "security"]
        assert len(security_issues) > 0, "Should find security issues"
        for issue in security_issues:
            assert "severity" in issue, "Issue should have severity"
            assert "remediation" in issue, "Issue should have remediation"
            assert issue["severity"] in ["blocker", "major", "minor", "cosmetic"]
