"""Demo runner with nice output formatting.

Provides DemoRunner class and run_all_demos() function for running
all three LuminaMind demo applications.
"""
import sys
import time
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.tree import Tree
except ImportError:
    # Fallback if rich is not available
    Console = None
    Panel = None
    Progress = None
    Tree = None


class DemoRunner:
    """Runs LuminaMind demo applications with nice formatting.

    Demo applications:
        - Frontend design demo (run_frontend_demo)
        - Full-stack app demo (run_fullstack_demo)
        - Code review demo (run_codereview_demo)

    Usage:
        runner = DemoRunner()
        runner.run_frontend_demo()
        runner.run_all_demos()
    """

    def __init__(self, verbose: bool = True):
        """Initialize the demo runner.

        Args:
            verbose: Whether to print detailed progress output
        """
        self.verbose = verbose
        self.console = Console() if Console else None

    def _print_header(self, title: str, description: str) -> None:
        """Print a formatted header for a demo.

        Args:
            title: Demo title
            description: Demo description
        """
        if self.console:
            self.console.print(Panel.fit(
                f"[bold cyan]{title}[/]\n[dim]{description}[/]",
                border_style="cyan"
            ))
        else:
            print(f"\n{'='*60}")
            print(f"{title}")
            print(f"{description}")
            print('='*60)

    def _print_success(self, message: str) -> None:
        """Print a success message."""
        if self.console:
            self.console.print(f"[green]✓ {message}[/]")
        else:
            print(f"SUCCESS: {message}")

    def _print_error(self, message: str) -> None:
        """Print an error message."""
        if self.console:
            self.console.print(f"[red]✗ {message}[/]")
        else:
            print(f"ERROR: {message}")

    def _print_info(self, message: str) -> None:
        """Print an info message."""
        if self.console:
            self.console.print(f"[dim]{message}[/]")
        else:
            print(f"INFO: {message}")

    def run_frontend_demo(self) -> dict:
        """Run the frontend design demo.

        Creates a DeepAgent instance and runs a frontend design task,
        then uses the EvaluatorAgent to score the output.

        Returns:
            Dictionary with demo results including generated code,
            evaluation scores, and pass/fail determination.
        """
        self._print_header(
            "Frontend Design Demo",
            "Generating and evaluating a responsive landing page"
        )

        try:
            from luminamind.demos.frontend_demo import run_frontend_demo
            result = run_frontend_demo()
            self._print_success("Frontend demo completed")
            return {"success": True, "result": result}
        except Exception as e:
            self._print_error(f"Frontend demo failed: {e}")
            return {"success": False, "error": str(e)}

    def run_fullstack_demo(self) -> dict:
        """Run the full-stack application demo.

        Creates a DeepAgent instance and runs a full-stack app task,
        then uses PlannerAgent and EvaluatorAgent to build and verify.

        Returns:
            Dictionary with demo results including generated project
            structure, key files, and evaluation scores.
        """
        self._print_header(
            "Full-Stack App Demo",
            "Generating a FastAPI backend with React frontend"
        )

        try:
            from luminamind.demos.fullstack_demo import run_fullstack_demo
            result = run_fullstack_demo()
            self._print_success("Full-stack demo completed")
            return {"success": True, "result": result}
        except Exception as e:
            self._print_error(f"Full-stack demo failed: {e}")
            return {"success": False, "error": str(e)}

    def run_codereview_demo(self) -> dict:
        """Run the code review demo.

        Creates a DeepAgent instance and evaluates sample buggy code
        using the EvaluatorAgent with security criteria.

        Returns:
            Dictionary with demo results including detected issues,
            severity ratings, and security score.
        """
        self._print_header(
            "Code Review Demo",
            "Detecting security vulnerabilities in sample code"
        )

        try:
            from luminamind.demos.codereview_demo import run_codereview_demo
            result = run_codereview_demo()
            self._print_success("Code review demo completed")
            return {"success": True, "result": result}
        except Exception as e:
            self._print_error(f"Code review demo failed: {e}")
            return {"success": False, "error": str(e)}

    def run_all_demos(self) -> dict:
        """Run all three demo applications in sequence.

        Returns:
            Dictionary with overall success status and individual
            demo results.
        """
        self._print_header(
            "LuminaMind Harness Demo Suite",
            "Running all demonstrations: Frontend, Full-Stack, Code Review"
        )

        start_time = time.time()
        results = {
            "frontend": None,
            "fullstack": None,
            "codereview": None,
        }

        demos = [
            ("Frontend Design", "frontend", self.run_frontend_demo),
            ("Full-Stack App", "fullstack", self.run_fullstack_demo),
            ("Code Review", "codereview", self.run_codereview_demo),
        ]

        for demo_name, demo_key, demo_func in demos:
            self._print_info(f"\nRunning {demo_name} demo...")
            try:
                results[demo_key] = demo_func()
            except Exception as e:
                self._print_error(f"{demo_name} demo failed with exception: {e}")
                results[demo_key] = {"success": False, "error": str(e)}

        elapsed = time.time() - start_time

        # Summary
        if self.console:
            from rich.table import Table
            table = Table(title="Demo Results Summary")
            table.add_column("Demo", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Duration", style="dim")

            for demo_name, demo_key, _ in demos:
                result = results[demo_key]
                status = "✓ PASS" if (result and result.get("success")) else "✗ FAIL"
                table.add_row(demo_name, status, f"{elapsed:.1f}s")

            self.console.print(table)
        else:
            print(f"\n{'='*60}")
            print("Demo Results Summary")
            print('='*60)
            for demo_name, demo_key, _ in demos:
                result = results[demo_key]
                status = "PASS" if (result and result.get("success")) else "FAIL"
                print(f"  {demo_name}: {status}")

        overall_success = all(
            r and r.get("success", False) for r in results.values()
        )

        return {
            "success": overall_success,
            "results": results,
            "duration_seconds": elapsed,
        }


def run_all_demos() -> dict:
    """Run all demos and return combined results.

    This is the main entry point for running the demo suite.

    Returns:
        Dictionary with overall success and individual demo results.
    """
    runner = DemoRunner(verbose=True)
    return runner.run_all_demos()


# CLI entry point
if __name__ == "__main__":
    print("Starting LuminaMind Demo Suite...\n")
    result = run_all_demos()

    if result.get("success"):
        print("\n✓ All demos completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Some demos failed. Check output for details.")
        sys.exit(1)