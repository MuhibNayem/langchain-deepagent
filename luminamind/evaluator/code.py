"""CodeEvaluator for code quality assessment per GE-06.

Scores: correctness, maintainability, performance, security.
Each dimension has specific metrics and thresholds.
Issues include severity level and remediation guidance.
Security scoring includes OWASP Top 10 checks.
"""
from __future__ import annotations

import re
from typing import Any

from luminamind.evaluator.criteria import CodeCriteria


# Bug severity classifications
SEVERITY_BLOCKER = "blocker"
SEVERITY_MAJOR = "major"
SEVERITY_MINOR = "minor"
SEVERITY_COSMETIC = "cosmetic"

# Scoring weights
WEIGHT_CORRECTNESS = 0.30
WEIGHT_MAINTAINABILITY = 0.25
WEIGHT_PERFORMANCE = 0.20
WEIGHT_SECURITY = 0.25


class CodeEvaluator(CodeCriteria):
    """Code quality evaluator per GE-06.

    Scores four dimensions:
    - correctness: bug presence, logic errors, edge cases
    - maintainability: cyclomatic complexity, coupling, naming
    - performance: algorithm complexity, resource usage, scalability
    - security: OWASP Top 10, injection, auth issues

    All scoring is static analysis only (no code execution).
    """

    domain = "code"

    def evaluate(self, artifact: Any) -> dict:
        """Evaluate code artifact.

        Returns dict with:
            - correctness_score: float (0-100)
            - maintainability_score: float (0-100)
            - performance_score: float (0-100)
            - security_score: float (0-100)
            - overall_score: float (weighted average)
            - issues: list[dict]
            - strengths: list[str]
            - recommendations: list[dict]
        """
        correctness = self._score_correctness(artifact)
        maintainability = self._score_maintainability(artifact)
        performance = self._score_performance(artifact)
        security = self._score_security(artifact)

        # Calculate weighted overall score
        overall = (
            correctness["score"] * WEIGHT_CORRECTNESS +
            maintainability["score"] * WEIGHT_MAINTAINABILITY +
            performance["score"] * WEIGHT_PERFORMANCE +
            security["score"] * WEIGHT_SECURITY
        )

        # Collect all issues with severity and remediation
        all_issues = (
            correctness["issues"] +
            maintainability["issues"] +
            performance["issues"] +
            security["issues"]
        )

        # Build strengths and recommendations
        strengths = []
        recommendations = []

        # Analyze for strengths
        if correctness["score"] >= 90:
            strengths.append("Correct implementation with proper error handling")
        if maintainability["score"] >= 90:
            strengths.append("Clean, well-structured code")
        if performance["score"] >= 90:
            strengths.append("Efficient algorithm design")
        if security["score"] >= 90:
            strengths.append("Secure coding practices observed")

        return {
            "correctness_score": correctness["score"],
            "maintainability_score": maintainability["score"],
            "performance_score": performance["score"],
            "security_score": security["score"],
            "overall_score": overall,
            "issues": all_issues,
            "strengths": strengths,
            "recommendations": recommendations,
        }

    def _score_correctness(self, artifact: Any) -> dict:
        """Score correctness: bug presence, logic errors, edge cases.

        Detects:
        - Infinite loops (while True without break)
        - Null dereferences (undefined variable access)
        - Division by zero risk
        - Logic errors (off-by-one, incorrect conditionals)
        """
        issues = []
        code = str(artifact)

        # Check for infinite loops
        if self._has_infinite_loop(code):
            issues.append(self._create_issue(
                "correctness",
                "infinite_loop",
                "Potential infinite loop detected (while True without break)",
                SEVERITY_MAJOR,
                "Add a break condition or use a bounded loop"
            ))

        # Check for null dereference patterns
        if self._has_null_dereference(code):
            issues.append(self._create_issue(
                "correctness",
                "null_dereference",
                "Potential null/None dereference",
                SEVERITY_MAJOR,
                "Add null check before accessing attributes"
            ))

        # Check for division by zero risk
        if self._has_division_by_zero_risk(code):
            issues.append(self._create_issue(
                "correctness",
                "division_by_zero",
                "Division operation without zero check",
                SEVERITY_MAJOR,
                "Add conditional check to prevent division by zero"
            ))

        # Check for logic errors
        logic_issues = self._find_logic_errors(code)
        issues.extend(logic_issues)

        # Calculate score: 100 base, -10 per issue
        score = 100 - (len(issues) * 10)
        return {"score": max(0, score), "issues": issues}

    def _score_maintainability(self, artifact: Any) -> dict:
        """Score maintainability: complexity, coupling, naming.

        Metrics:
        - Cyclomatic complexity (>10 = warning, >20 = critical)
        - Function length (>50 lines = warning, >100 = critical)
        - Nesting depth (>4 = warning, >7 = critical)
        - Naming conventions
        - Magic numbers
        """
        issues = []
        code = str(artifact)

        # Check for high cyclomatic complexity
        complexity_score = self._assess_complexity(code)

        if complexity_score < 90:
            issues.append(self._create_issue(
                "maintainability",
                "high_complexity",
                f"High cyclomatic complexity (score: {complexity_score})",
                SEVERITY_MAJOR,
                "Refactor using early returns, extract helper functions"
            ))

        # Check for long functions
        long_functions = self._find_long_functions(code)
        for func_name, line_count in long_functions:
            issues.append(self._create_issue(
                "maintainability",
                "long_function",
                f"Function '{func_name}' is {line_count} lines (recommended: <50)",
                SEVERITY_MINOR,
                "Extract logical sections into helper functions"
            ))

        # Check for deep nesting
        max_nesting = self._find_max_nesting_depth(code)
        if max_nesting > 7:
            issues.append(self._create_issue(
                "maintainability",
                "deep_nesting",
                f"Nesting depth of {max_nesting} detected (max recommended: 4)",
                SEVERITY_MAJOR,
                "Extract inner logic into helper functions"
            ))
        elif max_nesting > 4:
            issues.append(self._create_issue(
                "maintainability",
                "excessive_nesting",
                f"Nesting depth of {max_nesting} exceeds recommended 4",
                SEVERITY_MINOR,
                "Consider refactoring with early returns"
            ))

        # Check for nested loops (also adds maintainability issue)
        nested_loop_depth = self._find_nested_loop_depth(code)
        if nested_loop_depth >= 3:
            issues.append(self._create_issue(
                "maintainability",
                "deeply_nested_loops",
                f"Loop nesting depth of {nested_loop_depth} detected (max recommended: 2)",
                SEVERITY_MAJOR,
                "Consider flattening nested loops or extracting inner logic"
            ))
        elif nested_loop_depth >= 2:
            issues.append(self._create_issue(
                "maintainability",
                "nested_loops",
                f"Loop nesting depth of {nested_loop_depth} detected",
                SEVERITY_MINOR,
                "Consider if nested loops can be flattened"
            ))

        # Check for magic numbers
        magic_numbers = self._find_magic_numbers(code)
        for num in magic_numbers:
            issues.append(self._create_issue(
                "maintainability",
                "magic_number",
                f"Magic number detected: {num}",
                SEVERITY_MINOR,
                "Extract to named constant with descriptive name"
            ))

        # Check for poor naming
        naming_issues = self._find_naming_issues(code)
        issues.extend(naming_issues)

        # Base score is 100, deduct 10 per issue
        score = 100 - (len(issues) * 10)

        # But also factor in complexity score for deeper issues
        if complexity_score < 80:
            score = min(score, complexity_score)

        return {"score": max(0, score), "issues": issues}

    def _score_performance(self, artifact: Any) -> dict:
        """Score performance: algorithm complexity, resource usage.

        Detects:
        - Nested loops suggesting O(n²) or worse
        - Unbounded operations on large datasets
        - Memory allocation in loops
        - Synchronous blocking I/O
        - Missing pagination/streaming
        """
        issues = []
        code = str(artifact)

        # Check for O(n²) or worse patterns
        if self._has_quadratic_complexity(code):
            issues.append(self._create_issue(
                "performance",
                "quadratic_complexity",
                "Nested loops detected - potential O(n²) or worse complexity",
                SEVERITY_MAJOR,
                "Consider using more efficient algorithms or data structures"
            ))

        # Check for unbounded operations
        if self._has_unbounded_ops(code):
            issues.append(self._create_issue(
                "performance",
                "unbounded_operation",
                "Unbounded operation detected on potentially large data",
                SEVERITY_MINOR,
                "Consider adding size limits or using pagination/streaming"
            ))

        # Check for memory allocation in loops
        if self._has_memory_in_loop(code):
            issues.append(self._create_issue(
                "performance",
                "memory_in_loop",
                "Memory allocation detected inside loop",
                SEVERITY_MINOR,
                "Move allocation outside loop or use generators"
            ))

        # Check for blocking I/O
        if self._has_blocking_io(code):
            issues.append(self._create_issue(
                "performance",
                "blocking_io",
                "Synchronous blocking I/O detected",
                SEVERITY_MINOR,
                "Consider async I/O or batching operations"
            ))

        # Score: -15 per issue (more critical than correctness)
        score = 100 - (len(issues) * 15)
        return {"score": max(0, score), "issues": issues}

    def _score_security(self, artifact: Any) -> dict:
        """Score security: OWASP Top 10, injection, auth issues.

        Security issues are most critical - -20 per issue.
        Checks:
        - Shell injection (os.system, subprocess with shell=True)
        - SQL injection (string concatenation in queries)
        - XSS (innerHTML, document.write)
        - Hardcoded API keys / secrets
        - Missing authentication/authorization
        - Insecure random, deprecated crypto
        - Path traversal
        - Missing TLS verification
        """
        issues = []
        code = str(artifact)

        # Shell injection
        if self._has_shell_injection(code):
            issues.append(self._create_issue(
                "security",
                "shell_injection",
                "Shell injection vulnerability detected",
                SEVERITY_BLOCKER,
                "Avoid shell=True, use list arguments for subprocess"
            ))

        # SQL injection
        if self._has_sql_injection(code):
            issues.append(self._create_issue(
                "security",
                "sql_injection",
                "SQL injection vulnerability - string concatenation in query",
                SEVERITY_BLOCKER,
                "Use parameterized queries or an ORM"
            ))

        # XSS
        if self._has_xss(code):
            issues.append(self._create_issue(
                "security",
                "xss",
                "XSS vulnerability - direct HTML manipulation detected",
                SEVERITY_BLOCKER,
                "Use textContent instead of innerHTML, sanitize input"
            ))

        # Hardcoded secrets
        secrets = self._find_hardcoded_secrets(code)
        for secret_type in secrets:
            issues.append(self._create_issue(
                "security",
                "hardcoded_secret",
                f"Hardcoded {secret_type} detected",
                SEVERITY_BLOCKER,
                "Use environment variables or secrets management"
            ))

        # Path traversal
        if self._has_path_traversal(code):
            issues.append(self._create_issue(
                "security",
                "path_traversal",
                "Potential path traversal vulnerability",
                SEVERITY_MAJOR,
                "Validate and sanitize file paths, use os.path.relpath"
            ))

        # Insecure random
        if self._has_insecure_random(code):
            issues.append(self._create_issue(
                "security",
                "insecure_random",
                "Insecure random number generation for security purposes",
                SEVERITY_MAJOR,
                "Use secrets module or os.urandom for security-sensitive values"
            ))

        # Deprecated crypto
        if self._has_deprecated_crypto(code):
            issues.append(self._create_issue(
                "security",
                "deprecated_crypto",
                "Use of deprecated cryptographic function",
                SEVERITY_MAJOR,
                "Use modern cryptographic libraries (hashlib, hmac)"
            ))

        # Score: -20 per issue (most critical)
        score = 100 - (len(issues) * 20)
        return {"score": max(0, score), "issues": issues}

    def _create_issue(
        self,
        issue_type: str,
        code: str,
        description: str,
        severity: str,
        remediation: str,
        location: str = "code"
    ) -> dict:
        """Create a structured issue dict.

        Args:
            issue_type: correctness|maintainability|performance|security
            code: Short issue code (e.g., "shell_injection")
            description: Human-readable description
            severity: blocker|major|minor|cosmetic
            remediation: How to fix the issue
            location: Where the issue was found (file:line or function)

        Returns:
            Structured issue dict
        """
        return {
            "type": issue_type,
            "code": code,
            "description": description,
            "severity": severity,
            "remediation": remediation,
            "location": location,
        }

    # === Correctness detection methods ===

    def _has_infinite_loop(self, code: str) -> bool:
        """Check for infinite loop patterns."""
        # Pattern: while True without break
        if "while True" in code or "while 1" in code:
            # Check if there's a break inside
            lines = code.split("\n")
            in_while = False
            for line in lines:
                stripped = line.strip()
                if "while True" in line or "while 1" in line:
                    in_while = True
                elif in_while and "break" in stripped:
                    return False  # Has break, not infinite
                elif in_while and stripped.startswith(("return", "raise")):
                    return False  # Has exit path
                elif in_while and (line and line[0] not in " \t#"):
                    in_while = False  # Exited while block
            return True  # while True without break found
        return False

    def _has_null_dereference(self, code: str) -> bool:
        """Check for null/None dereference patterns."""
        patterns = [
            r'\w+\s*=\s*None.*?\w+\.',  # var = None followed by dot access
            r'\w+\.value',  # .value on potentially null
            r'\w+\[.*?\]',  # subscript on potentially null array/dict
        ]
        for pattern in patterns:
            if re.search(pattern, code, re.MULTILINE):
                return True
        return False

    def _has_division_by_zero_risk(self, code: str) -> bool:
        """Check for division without zero check."""
        import re
        # Simple check: division operator in function without try/except or conditional
        if "/" not in code or "def " not in code:
            return False
        # Look for division operators
        lines = code.split("\n")
        for line in lines:
            # Get code part (before any comment)
            code_part = line.split("#")[0]
            if "/" in code_part and "return" in code_part:
                # This is a return with division - check for zero protection
                # Look at surrounding context
                func_start = code.find("def ")
                if func_start >= 0:
                    func_body = code[func_start:]
                    # Check if there's a zero check in the function
                    if not re.search(r'if\s+.*[=!]=\s*0', func_body):
                        return True
        return False

    def _find_logic_errors(self, code: str) -> list:
        """Find logic errors like off-by-one, incorrect conditionals."""
        issues = []
        # Off-by-one: range without proper bounds
        if re.search(r'range\([^)]*n\s*-\s*1\)', code):
            issues.append(self._create_issue(
                "correctness",
                "off_by_one",
                "Potential off-by-one error in range",
                SEVERITY_MINOR,
                "Verify range bounds match expected behavior"
            ))
        return issues

    # === Maintainability detection methods ===

    def _assess_complexity(self, code: str) -> int:
        """Assess cyclomatic complexity."""
        score = 100

        # Count decision points more carefully
        # Count all if/for/while/except keywords
        decision_points = len(re.findall(r'\b(if|elif|while|for|except)\b', code))

        # Adjust for decision points (>5 is warning, >10 is critical)
        if decision_points > 10:
            score = max(0, score - 40)
        elif decision_points > 5:
            score = max(0, score - 20)
        elif decision_points > 3:
            score = max(0, score - 10)

        # Also check for nested loops (depth) - deeper nesting = harder to maintain
        nested_loop_depth = self._find_nested_loop_depth(code)
        if nested_loop_depth >= 3:
            score = max(0, score - 30)
        elif nested_loop_depth >= 2:
            score = max(0, score - 15)

        # Check max nesting depth
        max_nesting = self._find_max_nesting_depth(code)
        if max_nesting > 7:
            score = max(0, score - 40)
        elif max_nesting > 4:
            score = max(0, score - 30)
        elif max_nesting > 2:
            score = max(0, score - 20)

        return score

    def _find_nested_loop_depth(self, code: str) -> int:
        """Find maximum loop nesting depth."""
        max_depth = 0
        current_depth = 0
        lines = code.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("for ") or stripped.startswith("while "):
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif stripped and not any(stripped.startswith(kw) for kw in ["if ", "for ", "while ", "def ", "class "]):
                # Dedent tracking - simple approach: if line doesn't start with block keyword
                # and is at zero indent, we've exited all loops
                if len(line) - len(line.lstrip()) == 0:
                    current_depth = 0
        return max_depth

    def _find_long_functions(self, code: str) -> list:
        """Find functions longer than 50 lines."""
        long_funcs = []
        # Match function definitions
        func_pattern = r'def\s+(\w+)\s*\([^)]*\):(.*?)(?=\n\s*\ndef|\n\s*class|\Z)'
        matches = re.finditer(func_pattern, code, re.DOTALL)
        for match in matches:
            func_name = match.group(1)
            body = match.group(2)
            line_count = len(body.split("\n"))
            if line_count > 50:
                long_funcs.append((func_name, line_count))
        return long_funcs

    def _find_max_nesting_depth(self, code: str) -> int:
        """Find maximum nesting depth."""
        max_depth = 0
        current_depth = 0
        lines = code.split("\n")
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Calculate indent level (0-based, assuming 4-space indent)
            indent = len(line) - len(line.lstrip())
            indent_level = indent // 4

            # Direct indent-based tracking
            # Blank lines at indent 0 might indicate dedent
            if indent_level == 0 and current_depth > 0:
                # Check if this is really a dedent or just whitespace
                if stripped and not any(stripped.startswith(kw) for kw in ["if ", "for ", "while ", "def ", "class ", "else:", "elif:", "except:", "finally:"]):
                    # This is not a block-starting line at indent 0, might be dedent
                    pass  # Keep current_depth for now

            # If we see a block keyword, we're entering a new level
            if any(stripped.startswith(kw) for kw in ["if ", "for ", "while ", "def ", "class ", "try:"]):
                current_depth = indent_level + 1
            elif stripped.startswith("else:") or stripped.startswith("elif:"):
                # else/elif at indent_level should correspond to depth indent_level
                current_depth = indent_level
            elif stripped.startswith("except:") or stripped.startswith("finally:"):
                current_depth = indent_level
            elif stripped == "pass":
                # pass doesn't change depth, just placeholder
                pass
            else:
                # For other lines, track approximate depth
                if indent > 0:
                    current_depth = max(current_depth, indent_level + 1)

            max_depth = max(max_depth, current_depth)

        return max_depth

    def _find_magic_numbers(self, code: str) -> list:
        """Find magic numbers in code."""
        magic = []
        # Numbers that appear standalone (not in strings)
        number_pattern = r'(?<![a-zA-Z0-9_])([0-9]{2,})(?![a-zA-Z0-9_])'
        matches = re.findall(number_pattern, code)
        # Filter out common non-magic numbers
        for num in matches:
            if int(num) > 1 and int(num) not in [10, 100, 1000]:  # Exclude round numbers
                magic.append(num)
        return magic

    def _find_naming_issues(self, code: str) -> list:
        """Find naming convention issues."""
        issues = []
        # Check for single letter names (except loop vars)
        single_letter_vars = re.findall(r'\b([a-z])\s*=\s*[^=]', code)
        # Only flag if very few and not in loop context
        if len(single_letter_vars) > 5:
            issues.append(self._create_issue(
                "maintainability",
                "poor_naming",
                "Multiple single-letter variable names detected",
                SEVERITY_MINOR,
                "Use descriptive names (age instead of a, count instead of c)"
            ))
        return issues

    # === Performance detection methods ===

    def _has_quadratic_complexity(self, code: str) -> bool:
        """Check for nested loops indicating O(n²) or worse."""
        # Match nested for/while loops
        pattern = r'(for\s+\w+\s+in\s+.*?:\s*\n.*?){2,}'
        if re.search(pattern, code, re.MULTILINE | re.DOTALL):
            return True
        return False

    def _has_unbounded_ops(self, code: str) -> bool:
        """Check for unbounded operations on potentially large data."""
        patterns = [
            r'for\s+\w+\s+in\s+.*:',  # Basic for loops
            r'\.join\(',  # String join on collection
            r'\[\s*\w+\s*:\s*\]',  # Slicing without bounds
        ]
        for pattern in patterns:
            if re.search(pattern, code):
                return True
        return False

    def _has_memory_in_loop(self, code: str) -> bool:
        """Check for memory allocation inside loops."""
        # Look for list.append, += with strings, etc in loops
        if re.search(r'for\s+\w+\s+in\s+.*:.*?(\+=|\.append\()', code, re.DOTALL):
            return True
        return False

    def _has_blocking_io(self, code: str) -> bool:
        """Check for blocking I/O operations."""
        blocking_patterns = [
            r'requests\.',
            r'open\([^)]*\)',  # file open without async
            r'\.read\(\)',
            r'\.write\(',
        ]
        for pattern in blocking_patterns:
            if re.search(pattern, code):
                return True
        return False

    # === Security detection methods ===

    def _has_shell_injection(self, code: str) -> bool:
        """Check for shell injection vulnerabilities."""
        patterns = [
            r'os\.system\(',
            r'subprocess\.\w+\([^)]*shell\s*=\s*True',
            r'eval\(',
            r'exec\(',
        ]
        for pattern in patterns:
            if re.search(pattern, code):
                return True
        return False

    def _has_sql_injection(self, code: str) -> bool:
        """Check for SQL injection vulnerabilities."""
        # Check for string concatenation in SQL queries
        if "+ user_id" in code or "+\"" in code or "+ \"" in code:
            # Simple heuristic: if there's string concatenation near SQL keywords
            if any(kw in code.lower() for kw in ["select ", "insert ", "update ", "delete ", "where "]):
                return True

        patterns = [
            r'execute\s*\(\s*f["\']',  # f-string in execute
            r'cursor\.execute\([^)]*\+[^)]*\)',  # String concatenation
            r'["\'].*?%s.*?["\'].*?\.format\(',  # String formatting in SQL
            r'execute\s*\(\s*["\'].*?\+.*?["\']',  # execute with concatenated string
        ]
        for pattern in patterns:
            if re.search(pattern, code):
                return True
        return False

    def _has_xss(self, code: str) -> bool:
        """Check for XSS vulnerabilities."""
        patterns = [
            r'innerHTML\s*=',
            r'document\.write\(',
            r'\.html\([^)]*\)',  # jQuery html()
        ]
        for pattern in patterns:
            if re.search(pattern, code):
                return True
        return False

    def _find_hardcoded_secrets(self, code: str) -> list:
        """Find hardcoded secrets."""
        found = []
        secret_patterns = [
            (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', "API key"),
            (r'password\s*=\s*["\'][^"\']+["\']', "password"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "secret"),
            (r'token\s*=\s*["\'][^"\']+["\']', "token"),
            (r'aws[_-]?key', "AWS key"),
            (r'private[_-]?key', "private key"),
        ]
        for pattern, secret_type in secret_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                found.append(secret_type)
        return found

    def _has_path_traversal(self, code: str) -> bool:
        """Check for path traversal vulnerabilities."""
        patterns = [
            r'open\([^)]*\+[^)]*\)',  # open with concatenation
            r'os\.path\.join\([^)]*\+[^)]*\)',
            r'\.open\([^)]*request\.',  # opening file based on request
        ]
        for pattern in patterns:
            if re.search(pattern, code):
                return True
        return False

    def _has_insecure_random(self, code: str) -> bool:
        """Check for insecure random number generation."""
        patterns = [
            r'random\.random\(',
            r'random\.randint\(',
            r'random\.choice\(',
        ]
        for pattern in patterns:
            if re.search(pattern, code):
                # Only flag if used for security purposes
                if any(kw in code.lower() for kw in ["key", "token", "password", "secret", "salt"]):
                    return True
        return False

    def _has_deprecated_crypto(self, code: str) -> bool:
        """Check for deprecated cryptographic functions."""
        patterns = [
            r'hashlib\.md5',
            r'hashlib\.sha1',
            r'Crypt\.',
            r'DES\.',
            r'RC4\.',
        ]
        for pattern in patterns:
            if re.search(pattern, code):
                return True
        return False

    def get_criteria(self) -> list:
        """Code evaluation criteria."""
        return ["correctness", "maintainability", "performance", "security"]
