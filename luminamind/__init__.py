"""LuminaMind - Autonomous Coding Agent Harness

Integrates: Context/Memory, Generator-Evaluator, Planner-Sprint,
Live Verification, Tool/Prompt Optimization, Production Hardening

Component Inventory (Phase 1-6):
- Phase 1: Context & Memory
  from luminamind.context import ContextManager, WorkingMemory

- Phase 2: Generator-Evaluator
  from luminamind.evaluator import EvaluatorAgent, FeedbackBridge, CriteriaEngine
  from luminamind.evaluator.iteration import IterationController, IterationStats
  from luminamind.evaluator.pipeline import RefinementPipeline, RefinementResult

- Phase 3: Planner & Sprint
  from luminamind.planner import PlannerAgent, SprintContract, ContractVerifier

- Phase 4: Live Verification
  from luminamind.evaluator.live_verifier import LiveVerifier
  from luminamind.evaluator.playwright_mcp_bridge import PlaywrightMCPBridge

- Phase 5: Tool & Prompt Optimization
  from luminamind.optimization import TokenBudget, CacheOptimizer

- Phase 6: Production Hardening
  from luminamind.safety import SafetyChecker, CircuitBreaker
  from luminamind.observability import HarnessMetrics
"""

from deepagents import create_deep_agent

from luminamind.config.env import load_project_env, validate_env
from luminamind.config.checkpointer import create_checkpointer, CheckpointConfig

from luminamind.evaluator import EvaluatorAgent, FeedbackBridge, CriteriaEngine
from luminamind.evaluator.iteration import IterationController, IterationStats
from luminamind.evaluator.pipeline import RefinementPipeline, RefinementResult

from luminamind.planner import PlannerAgent, SprintContract, ContractVerifier

from luminamind.hooks import HookEmitter, HookContext, LifecycleEvent, get_emitter

from luminamind.safety import CircuitBreaker, OutputValidator

from luminamind.observability import HarnessMetrics, start_metrics_server

__version__ = "1.0.0"

__all__ = [
    # Core
    "create_deep_agent",
    # Config
    "load_project_env",
    "validate_env",
    "create_checkpointer",
    "CheckpointConfig",
    # Evaluator
    "EvaluatorAgent",
    "FeedbackBridge",
    "CriteriaEngine",
    "IterationController",
    "IterationStats",
    "RefinementPipeline",
    "RefinementResult",
    # Planner
    "PlannerAgent",
    "SprintContract",
    "ContractVerifier",
    # Hooks
    "HookEmitter",
    "HookContext",
    "LifecycleEvent",
    "get_emitter",
    # Safety
    "CircuitBreaker",
    "OutputValidator",
    # Observability
    "HarnessMetrics",
    "start_metrics_server",
    # Version
    "__version__",
]