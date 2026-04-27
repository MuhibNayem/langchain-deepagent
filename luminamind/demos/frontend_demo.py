"""Frontend design demo using the LuminaMind EvaluatorAgent.

This demo showcases the harness capabilities by:
1. Creating a DeepAgent instance
2. Running a frontend design task
3. Using EvaluatorAgent to score the output
4. Displaying generated code and evaluation results
"""
import tempfile
import shutil
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.codeblock import CodeBlock
except ImportError:
    Console = None
    Panel = None
    CodeBlock = None


def run_frontend_demo() -> dict:
    """Run the frontend design demo.

    Creates a DeepAgent instance with a task to generate a responsive
    landing page, then uses EvaluatorAgent to evaluate the output.

    Returns:
        Dictionary with:
            - generated_code: The HTML/CSS code produced
            - evaluation: GradingResult with score, issues, feedback
            - passed: Boolean indicating if quality gate was met
            - temp_dir: Path to temporary output directory (will be cleaned)
    """
    console = Console() if Console else None

    if console:
        console.print("\n[bold]Task:[/bold] Create a responsive landing page for a SaaS product")
        console.print("  - Hero section with CTA")
        console.print("  - Features grid")
        console.print("  - Pricing table\n")

    # Sample generated frontend code (simulating DeepAgent output)
    # In a real scenario, this would come from DeepAgent.run()
    generated_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SaaS Landing Page</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 1200px; margin: 0 auto; padding: 0 20px; }
        header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 80px 0; text-align: center; }
        header h1 { font-size: 3rem; margin-bottom: 20px; }
        header p { font-size: 1.25rem; opacity: 0.9; margin-bottom: 30px; }
        .cta-button { display: inline-block; background: white; color: #667eea; padding: 15px 40px; border-radius: 50px; text-decoration: none; font-weight: bold; transition: transform 0.2s; }
        .cta-button:hover { transform: scale(1.05); }
        .features { padding: 80px 0; background: #f9f9f9; }
        .features h2 { text-align: center; font-size: 2.5rem; margin-bottom: 50px; }
        .features-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 30px; }
        .feature-card { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
        .feature-card h3 { font-size: 1.5rem; margin-bottom: 15px; color: #667eea; }
        .pricing { padding: 80px 0; }
        .pricing h2 { text-align: center; font-size: 2.5rem; margin-bottom: 50px; }
        .pricing-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 30px; }
        .pricing-card { border: 2px solid #eee; border-radius: 10px; padding: 40px; text-align: center; }
        .pricing-card.featured { border-color: #667eea; position: relative; }
        .pricing-card.featured::before { content: 'Popular'; position: absolute; top: -12px; left: 50%; transform: translateX(-50%); background: #667eea; color: white; padding: 5px 20px; border-radius: 20px; font-size: 0.875rem; }
        .price { font-size: 3rem; font-weight: bold; margin: 20px 0; }
        .price span { font-size: 1rem; font-weight: normal; }
        .pricing-features { list-style: none; margin: 20px 0; }
        .pricing-features li { padding: 10px 0; border-bottom: 1px solid #eee; }
        @media (max-width: 768px) { header h1 { font-size: 2rem; } }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>Build Better Products Faster</h1>
            <p>The all-in-one platform for modern development teams</p>
            <a href="#" class="cta-button">Start Free Trial</a>
        </div>
    </header>
    <section class="features">
        <div class="container">
            <h2>Features</h2>
            <div class="features-grid">
                <div class="feature-card">
                    <h3>⚡ Lightning Fast</h3>
                    <p>Optimized for speed with global CDN and edge computing</p>
                </div>
                <div class="feature-card">
                    <h3>🔒 Secure by Default</h3>
                    <p>Enterprise-grade security with SOC 2 compliance</p>
                </div>
                <div class="feature-card">
                    <h3>📊 Analytics Built-in</h3>
                    <p>Real-time insights and comprehensive reporting</p>
                </div>
            </div>
        </div>
    </section>
    <section class="pricing">
        <div class="container">
            <h2>Pricing Plans</h2>
            <div class="pricing-grid">
                <div class="pricing-card">
                    <h3>Starter</h3>
                    <div class="price">$9<span>/month</span></div>
                    <ul class="pricing-features">
                        <li>5 Team Members</li>
                        <li>10GB Storage</li>
                        <li>Basic Support</li>
                    </ul>
                </div>
                <div class="pricing-card featured">
                    <h3>Professional</h3>
                    <div class="price">$29<span>/month</span></div>
                    <ul class="pricing-features">
                        <li>25 Team Members</li>
                        <li>100GB Storage</li>
                        <li>Priority Support</li>
                    </ul>
                </div>
                <div class="pricing-card">
                    <h3>Enterprise</h3>
                    <div class="price">$99<span>/month</span></div>
                    <ul class="pricing-features">
                        <li>Unlimited Members</li>
                        <li>1TB Storage</li>
                        <li>24/7 Support</li>
                    </ul>
                </div>
            </div>
        </div>
    </section>
</body>
</html>"""

    # Create temp directory for output
    temp_dir = tempfile.mkdtemp(prefix="luminamind_frontend_")

    # Write the generated code
    output_path = Path(temp_dir) / "landing.html"
    output_path.write_text(generated_html)

    # Evaluate using EvaluatorAgent
    try:
        from luminamind.evaluator import EvaluatorAgent

        evaluator = EvaluatorAgent(max_iterations=3)

        if console:
            console.print("[yellow]Running evaluation...[/yellow]\n")

        evaluation = evaluator.evaluate(generated_html)

        # Determine pass/fail
        passed = evaluation.score >= 70.0

        if console:
            console.print(f"[bold]Generated Output:[/bold] {output_path.name}")
            console.print(f"[bold]Evaluation Score:[/bold] {evaluation.score:.1f}/100")
            console.print(f"[bold]Issues Found:[/bold] {len(evaluation.issues)}")
            if evaluation.issues:
                for issue in evaluation.issues:
                    console.print(f"  - {issue}")
            console.print(f"[bold]Status:[/bold] {'[green]PASS[/green]' if passed else '[red]FAIL[/red]'}")
            console.print(f"\n[bold]Feedback:[/bold]\n{evaluation.feedback}")

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

        return {
            "generated_code": generated_html,
            "evaluation": {
                "score": evaluation.score,
                "issues": evaluation.issues,
                "feedback": evaluation.feedback,
                "iterations": evaluation.iteration,
            },
            "passed": passed,
            "temp_dir": temp_dir,
        }

    except ImportError as e:
        error_msg = f"EvaluatorAgent not available: {e}"
        if console:
            console.print(f"[red]Error:[/red] {error_msg}")
        return {
            "generated_code": generated_html,
            "evaluation": None,
            "passed": False,
            "error": error_msg,
            "temp_dir": temp_dir,
        }
    except Exception as e:
        error_msg = f"Evaluation failed: {e}"
        if console:
            console.print(f"[red]Error:[/red] {error_msg}")
        return {
            "generated_code": generated_html,
            "evaluation": None,
            "passed": False,
            "error": error_msg,
            "temp_dir": temp_dir,
        }


if __name__ == "__main__":
    result = run_frontend_demo()
    print(f"\nResult: {'PASS' if result['passed'] else 'FAIL'}")