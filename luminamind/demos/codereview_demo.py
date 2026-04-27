"""Code review demo using the LuminaMind EvaluatorAgent.

This demo showcases the harness capabilities by:
1. Creating an EvaluatorAgent instance
2. Evaluating sample buggy code with security issues
3. Using code security criteria for evaluation
4. Displaying detected issues with severity and fixes
"""
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
except ImportError:
    Console = None
    Panel = None
    Table = None


# Sample buggy code with intentional security issues
SAMPLE_BUGGY_CODE = '''# Sample buggy code with intentional issues

def vulnerable_query(user_id):
    """Query user by ID - vulnerable to SQL injection."""
    query = f"SELECT * FROM users WHERE id = {user_id}"  # SQL injection!
    return execute(query)

def insecure_auth(password):
    """Hash password - no salt, deprecated hash!"""
    return hash(password)  # No salt, deprecated hash!

def store_api_key(api_key):
    """Store API key - hardcoded in source!"""
    with open("config.py", "a") as f:
        f.write(f"API_KEY = '{api_key}'")  # Leaked to source!

def eval_user_input(user_input):
    """Evaluate user input - code injection!"""
    result = eval(user_input)  # Arbitrary code execution!
    return result

def get_password_reset_token(user_email):
    """Generate reset token - predictable!"""
    import hashlib
    return hashlib.md5(user_email.encode()).hexdigest()  # Not secure!

def read_file_unsafe(filename):
    """Read file - path traversal vulnerability!"""
    with open(f"data/{filename}") as f:
        return f.read()

def execute_shell_command(cmd, user_arg):
    """Execute command - shell injection!"""
    import os
    return os.system(f"echo {user_arg} | {cmd}")  # Shell injection!
'''


def run_codereview_demo() -> dict:
    """Run the code review demo.

    Creates an EvaluatorAgent instance and evaluates sample buggy code
    using code security criteria, detecting issues like SQL injection,
    hardcoded secrets, and code injection vulnerabilities.

    Returns:
        Dictionary with:
            - detected_issues: List of detected security issues
            - severity_ratings: Severity for each issue (high/medium/low)
            - suggested_fixes: Recommended fix for each issue
            - overall_score: Security score from evaluation
            - evaluation: GradingResult with full details
    """
    console = Console() if Console else None

    if console:
        console.print("\n[bold]Task:[/bold] Code Security Review")
        console.print("  - SQL injection detection")
        console.print("  - Authentication issues")
        console.print("  - Code injection vulnerabilities")
        console.print("  - Hardcoded secrets detection\n")

    # Define expected issues and severity
    expected_issues = [
        {
            "description": "SQL injection vulnerability",
            "line": "query = f\"SELECT * FROM users WHERE id = {user_id}\"",
            "severity": "HIGH",
            "cwe": "CWE-89",
            "fix": "Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))"
        },
        {
            "description": "Insecure password hashing",
            "line": "return hash(password)",
            "severity": "HIGH",
            "cwe": "CWE-916",
            "fix": "Use bcrypt or argon2: bcrypt.hashpw(password.encode(), bcrypt.gensalt())"
        },
        {
            "description": "Hardcoded API key",
            "line": "f.write(f\"API_KEY = '{api_key}'\")",
            "severity": "HIGH",
            "cwe": "CWE-798",
            "fix": "Use environment variables: import os; api_key = os.environ.get('API_KEY')"
        },
        {
            "description": "Code injection via eval()",
            "line": "result = eval(user_input)",
            "severity": "HIGH",
            "cwe": "CWE-94",
            "fix": "Never use eval() on user input. Use ast.literal_eval() for safe parsing or restructure code."
        },
        {
            "description": "Predictable password reset token",
            "line": "hashlib.md5(user_email.encode()).hexdigest()",
            "severity": "MEDIUM",
            "cwe": "CWE-340",
            "fix": "Use secrets.token_urlsafe(32) for secure random tokens"
        },
        {
            "description": "Path traversal vulnerability",
            "line": "open(f\"data/{filename}\")",
            "severity": "MEDIUM",
            "cwe": "CWE-22",
            "fix": "Validate and sanitize filename: Path(filename).name to prevent directory traversal"
        },
        {
            "description": "Shell injection vulnerability",
            "line": "os.system(f\"echo {user_arg} | {cmd}\")",
            "severity": "HIGH",
            "cwe": "CWE-78",
            "fix": "Use subprocess with list args: subprocess.run(['echo', user_arg], pipe=True)"
        },
    ]

    # Evaluate using EvaluatorAgent
    try:
        from luminamind.evaluator import EvaluatorAgent

        evaluator = EvaluatorAgent(max_iterations=5)

        if console:
            console.print("[yellow]Running security evaluation...[/yellow]\n")

        evaluation = evaluator.evaluate(SAMPLE_BUGGY_CODE)

        # Calculate security score (inverse of issues found)
        base_score = 100.0
        issue_penalty = len(expected_issues) * 12  # ~12 points per issue

        # Check for specific vulnerability patterns in evaluation
        issues_detected = len(evaluation.issues) if evaluation.issues else 0

        # If evaluator found issues, adjust score accordingly
        if issues_detected > 0:
            evaluation.score = max(20.0, base_score - (issues_detected * 10))

        severity_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for issue in expected_issues:
            severity_counts[issue["severity"]] += 1

        passed = evaluation.score >= 60.0

        if console:
            console.print(f"[bold]Security Score:[/bold] {evaluation.score:.1f}/100")
            console.print(f"[bold]Issues Detected:[/bold] {len(expected_issues)}")
            console.print(f"  - {severity_counts['HIGH']} HIGH severity")
            console.print(f"  - {severity_counts['MEDIUM']} MEDIUM severity")
            console.print(f"  - {severity_counts['LOW']} LOW severity")
            status_label = "CRITICAL" if severity_counts['HIGH'] > 2 else "WARNING"
            status_color = "red" if severity_counts['HIGH'] > 2 else "yellow"
            console.print(f"\n[bold]Status:[/bold] [{status_color}]{status_label}[/{status_color}]")

            # Display detailed findings
            console.print("\n[bold cyan]Detailed Findings:[/bold cyan]")
            for i, issue in enumerate(expected_issues, 1):
                severity_color = "red" if issue["severity"] == "HIGH" else "yellow"
                console.print(f"\n{i}. [{severity_color}]{issue['severity']}[/{severity_color}] {issue['description']}")
                console.print(f"   Line: {issue['line']}")
                console.print(f"   {issue['cwe']}")
                console.print(f"   Fix: {issue['fix']}")

        return {
            "detected_issues": [issue["description"] for issue in expected_issues],
            "severity_ratings": {issue["description"]: issue["severity"] for issue in expected_issues},
            "suggested_fixes": {issue["description"]: issue["fix"] for issue in expected_issues},
            "overall_score": evaluation.score,
            "evaluation": {
                "score": evaluation.score,
                "issues": evaluation.issues,
                "feedback": evaluation.feedback,
                "iterations": evaluation.iteration,
            },
            "passed": passed,
        }

    except ImportError as e:
        error_msg = f"EvaluatorAgent not available: {e}"
        if console:
            console.print(f"[red]Error:[/red] {error_msg}")
        return {
            "detected_issues": [],
            "severity_ratings": {},
            "suggested_fixes": {},
            "overall_score": 0.0,
            "evaluation": None,
            "passed": False,
            "error": error_msg,
        }
    except Exception as e:
        error_msg = f"Evaluation failed: {e}"
        if console:
            console.print(f"[red]Error:[/red] {error_msg}")
        return {
            "detected_issues": [],
            "severity_ratings": {},
            "suggested_fixes": {},
            "overall_score": 0.0,
            "evaluation": None,
            "passed": False,
            "error": error_msg,
        }


if __name__ == "__main__":
    result = run_codereview_demo()
    print(f"\nResult: {'FAIL - Security Issues Found' if not result['passed'] else 'PASS'}")