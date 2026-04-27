"""Demo applications for LuminaMind harness.

This package contains demonstration applications that showcase the
integration of Phase 1-6 components in the LuminaMind harness.

Demos:
    - frontend_demo: Frontend design demo using evaluator
    - fullstack_demo: Full-stack application demo
    - codereview_demo: Code review demo using evaluator

Usage:
    from luminamind.demos import DemoRunner, run_all_demos

    # Run all demos
    run_all_demos()

    # Run specific demo
    from luminamind.demos import run_frontend_demo
    run_frontend_demo()
"""

from luminamind.demos.runner import DemoRunner, run_all_demos

__all__ = [
    "DemoRunner",
    "run_all_demos",
    "run_frontend_demo",
    "run_fullstack_demo",
    "run_codereview_demo",
]

__version__ = "1.0.0"