"""DeepAgent - Unified agent class integrating all Phase 1-6 components.

This module provides the DeepAgent class that orchestrates the full pipeline:
- Phase 1: Context & Memory
- Phase 2: Generator-Evaluator
- Phase 3: Planner & Sprint
- Phase 4: Live Verification
- Phase 5: Tool & Prompt Optimization
- Phase 6: Production Hardening
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict

from deepagents import create_deep_agent as _create_deep_agent

from .config.checkpointer import create_checkpointer, CheckpointConfig
from .config.env import load_project_env
from .py_tools.registry import PY_TOOL_REGISTRY

# Import Phase 2 components (with graceful degradation)
try:
    from luminamind.evaluator import EvaluatorAgent, FeedbackBridge, CriteriaEngine
    from luminamind.evaluator.iteration import IterationController
    _EVALUATOR_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Phase 2 (Generator-Evaluator) unavailable: {e}")
    _EVALUATOR_AVAILABLE = False
    EvaluatorAgent = None
    FeedbackBridge = None
    CriteriaEngine = None
    IterationController = None

# Import Phase 3 components (with graceful degradation)
try:
    from luminamind.planner import PlannerAgent, SprintContract, ContractVerifier
    _PLANNER_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Phase 3 (Planner & Sprint) unavailable: {e}")
    _PLANNER_AVAILABLE = False
    PlannerAgent = None
    SprintContract = None
    ContractVerifier = None

# Import Phase 4 LiveVerifier (with graceful degradation)
try:
    from luminamind.evaluator.live_verifier import LiveVerifier, VerificationConfig
    _LIVE_VERIFIER_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Phase 4 (Live Verification) unavailable: {e}")
    _LIVE_VERIFIER_AVAILABLE = False
    LiveVerifier = None
    VerificationConfig = None

# Import Phase 5 optimization (with graceful degradation)
try:
    from luminamind.optimization import TokenBudget, CacheOptimizer
    _OPTIMIZATION_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Phase 5 (Optimization) unavailable: {e}")
    _OPTIMIZATION_AVAILABLE = False
    TokenBudget = None
    CacheOptimizer = None

# Import Phase 6 safety and observability (with graceful degradation)
try:
    from luminamind.safety import CircuitBreaker, OutputValidator
    from luminamind.observability import HarnessMetrics
    _SAFETY_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Phase 6 (Safety/Observability) unavailable: {e}")
    _SAFETY_AVAILABLE = False
    CircuitBreaker = None
    OutputValidator = None
    HarnessMetrics = None

# Import lifecycle hooks
try:
    from luminamind.hooks import get_emitter, LifecycleEvent, HookContext
    _HOOKS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Lifecycle hooks unavailable: {e}")
    _HOOKS_AVAILABLE = False
    get_emitter = None
    LifecycleEvent = None
    HookContext = None

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent


class DeepAgentState(TypedDict):
    """State schema for the DeepAgent pipeline.

    Attributes:
        task: The current task description
        context: Working memory and context
        artifact: Current artifact under evaluation
        iteration: Current iteration count
        phase: Current phase in the pipeline
        result: Final result when complete
    """

    task: str
    context: dict | None
    artifact: Any
    iteration: int
    phase: str
    result: dict | None


@dataclass
class DeepAgentConfig:
    """Configuration for DeepAgent.

    Attributes:
        checkpointer_config: CheckpointConfig for session persistence
        enable_evaluator: Whether to enable Generator-Evaluator (Phase 2)
        enable_planner: Whether to enable Planner-Sprint (Phase 3)
        enable_live_verification: Whether to enable Live Verification (Phase 4)
        enable_optimization: Whether to enable Tool/Prompt Optimization (Phase 5)
        enable_safety: Whether to enable Safety and Observability (Phase 6)
        quality_gate: Minimum score threshold for quality gate (0-100)
        max_iterations: Maximum iterations for refinement loop
    """

    checkpointer_config: CheckpointConfig | None = None
    enable_evaluator: bool = True
    enable_planner: bool = True
    enable_live_verification: bool = True
    enable_optimization: bool = True
    enable_safety: bool = True
    quality_gate: float = 80.0
    max_iterations: int = 5


class DeepAgent:
    """Unified agent class integrating all Phase 1-6 components.

    Provides a single run(task) method that orchestrates the full pipeline
    with graceful degradation when optional components are unavailable.

    Args:
        config: DeepAgentConfig instance. Uses defaults if None.
    """

    def __init__(self, config: DeepAgentConfig | None = None):
        self.config = config or DeepAgentConfig()

        # Initialize lifecycle hooks
        self._emitter = get_emitter() if _HOOKS_AVAILABLE else None

        # Initialize Phase 2 components
        self._evaluator: EvaluatorAgent | None = None
        self._feedback_bridge: FeedbackBridge | None = None
        self._criteria_engine: CriteriaEngine | None = None
        self._iteration_controller: IterationController | None = None
        if _EVALUATOR_AVAILABLE and self.config.enable_evaluator:
            self._init_phase2()

        # Initialize Phase 3 components
        self._planner: PlannerAgent | None = None
        self._sprint_contract: SprintContract | None = None
        self._contract_verifier: ContractVerifier | None = None
        if _PLANNER_AVAILABLE and self.config.enable_planner:
            self._init_phase3()

        # Initialize Phase 4 components
        self._live_verifier: LiveVerifier | None = None
        if _LIVE_VERIFIER_AVAILABLE and self.config.enable_live_verification:
            self._init_phase4()

        # Import VerificationConfig for Phase 4
        if _LIVE_VERIFIER_AVAILABLE:
            from luminamind.evaluator.live_verifier import VerificationConfig

        # Initialize Phase 5 components
        self._token_budget: TokenBudget | None = None
        self._cache_optimizer: CacheOptimizer | None = None
        if _OPTIMIZATION_AVAILABLE and self.config.enable_optimization:
            self._init_phase5()

        # Initialize Phase 6 components
        self._circuit_breaker: CircuitBreaker | None = None
        self._output_validator: OutputValidator | None = None
        self._metrics: HarnessMetrics | None = None
        if _SAFETY_AVAILABLE and self.config.enable_safety:
            self._init_phase6()

        # Initialize the deepagents app
        self._app = self._create_app()
        self._initialized = True

        logger.info(
            "DeepAgent initialized",
            extra={
                "evaluator": _EVALUATOR_AVAILABLE and self.config.enable_evaluator,
                "planner": _PLANNER_AVAILABLE and self.config.enable_planner,
                "live_verification": _LIVE_VERIFIER_AVAILABLE and self.config.enable_live_verification,
                "optimization": _OPTIMIZATION_AVAILABLE and self.config.enable_optimization,
                "safety": _SAFETY_AVAILABLE and self.config.enable_safety,
            }
        )

    def _init_phase2(self) -> None:
        """Initialize Phase 2: Generator-Evaluator components."""
        try:
            self._evaluator = EvaluatorAgent()
            self._feedback_bridge = FeedbackBridge()
            self._criteria_engine = CriteriaEngine()
            self._iteration_controller = IterationController(
                evaluator=self._evaluator,
                max_iterations=self.config.max_iterations,
                quality_gate=self.config.quality_gate,
            )
            logger.debug("Phase 2 (Generator-Evaluator) initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Phase 2: {e}")
            self._evaluator = None

    def _init_phase3(self) -> None:
        """Initialize Phase 3: Planner & Sprint components."""
        try:
            self._planner = PlannerAgent()
            from luminamind.planner.spec import SpecDocument
            self._sprint_contract = SprintContract(
                id=str(uuid.uuid4()),
                spec=SpecDocument(
                    id=str(uuid.uuid4()),
                    title="Default Contract",
                    description="Auto-generated contract for DeepAgent initialization",
                    feature_request="Default feature request",
                ),
                parties=["planner", "evaluator"],
                timeline={"start": datetime.utcnow().isoformat(), "end": None},
                acceptance_criteria=[],
            )
            self._contract_verifier = ContractVerifier()
            logger.debug("Phase 3 (Planner & Sprint) initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Phase 3: {e}")
            self._planner = None

    def _init_phase4(self) -> None:
        """Initialize Phase 4: Live Verification components."""
        try:
            self._live_verifier = LiveVerifier(
                config=VerificationConfig()
            )
            logger.debug("Phase 4 (Live Verification) initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Phase 4: {e}")
            self._live_verifier = None

    def _init_phase5(self) -> None:
        """Initialize Phase 5: Tool & Prompt Optimization components."""
        try:
            self._token_budget = TokenBudget()
            self._cache_optimizer = CacheOptimizer()
            logger.debug("Phase 5 (Optimization) initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Phase 5: {e}")
            self._token_budget = None

    def _init_phase6(self) -> None:
        """Initialize Phase 6: Production Hardening components."""
        try:
            self._circuit_breaker = CircuitBreaker(name="deep_agent_main")
            self._output_validator = OutputValidator()
            self._metrics = HarnessMetrics()
            logger.debug("Phase 6 (Safety/Observability) initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Phase 6: {e}")
            self._circuit_breaker = None

    def _try_init_phase(self, phase_name: str, init_fn) -> Any:
        """Try to initialize a phase, returning None on failure with warning.

        Args:
            phase_name: Name of the phase for logging
            init_fn: Initialization function to call

        Returns:
            Initialized component or None
        """
        try:
            return init_fn()
        except Exception as e:
            logger.warning(f"Phase {phase_name} unavailable: {e}")
            return None

    def _create_app(self):
        """Create the underlying deepagents app.

        Returns:
            Configured deepagents app instance
        """
        load_project_env()

        from langchain_community.tools.file_management.copy import CopyFileTool
        from langchain_community.tools.file_management.delete import DeleteFileTool
        from langchain_community.tools.file_management.file_search import FileSearchTool
        from langchain_community.tools.file_management.list_dir import ListDirectoryTool
        from langchain_community.tools.file_management.move import MoveFileTool
        from langchain_community.tools.file_management.read import ReadFileTool
        from langchain_community.tools.file_management.write import WriteFileTool

        copy_file_tool = CopyFileTool()
        delete_file_tool = DeleteFileTool()
        file_search_tool = FileSearchTool()
        list_directory_tool = ListDirectoryTool()
        move_file_tool = MoveFileTool()
        read_file_tool = ReadFileTool()
        write_file_tool = WriteFileTool()

        def registry_tool(name: str):
            tool_obj = PY_TOOL_REGISTRY.get(name)
            if tool_obj is None:
                raise ValueError(f"Tool '{name}' is not registered in PY_TOOL_REGISTRY.")
            return tool_obj

        python_native_tools = list(PY_TOOL_REGISTRY.values())

        ALL_BASE_TOOLS = [
            copy_file_tool,
            delete_file_tool,
            file_search_tool,
            list_directory_tool,
            move_file_tool,
            read_file_tool,
            write_file_tool,
        ] + python_native_tools

        SYSTEM_PROMPT = """You are a deep autonomy agent that plans, researches, and edits codebases.

        - Create a todo list before diving into execution.
        - Use the filesystem tools to inspect, edit, and organize the repository.
        - When exploring unfamiliar directory structures, use the tree_view tool first to get a hierarchical overview.
        - Prefer the shell tool for commands that combine multiple steps.
        - Keep track of what each subagent is tackling so you can coordinate work.
        - Always summarize changes before finishing.
        - CRITICAL:
            - Before stopping, verify that ALL items in your todo list are completed. Do not stop if there are pending tasks.
            - Always use the designated subagent to perform the task. Never do the task yourself.
        """

        WEB_RESEARCH_SUBAGENT_PROMPT = """You are a focused research specialist.
        - Break the assigned question into crisp sub questions.
        - Use the web_search and crawling tools to gather facts and cite the strongest sources.
        - Return a structured, citation-rich answer that the main agent can use directly.
        """

        CODE_EXECUTOR_SUBAGENT_PROMPT = """You are a senior software engineer with commit access.
        - Inspect project files and understand the existing implementation.
        - Use shell and replace_in_file to make precise, minimal updates.
        - Run commands cautiously; read error output and retry with fixes.
        - Summarize every change you make so the main agent can keep context.
        - CRITICAL: If you have a list of files to create or modify, DO NOT STOP until you have processed ALL of them.
        - CRITICAL: Do not ask for confirmation for every single file if you have a batch of work. Execute the entire batch.
        """

        def build_subagents():
            research_agent = {
                "name": "web-researcher",
                "description": "Use for deep research, fact gathering, and synthesizing external knowledge.",
                "system_prompt": WEB_RESEARCH_SUBAGENT_PROMPT,
                "tools": [
                    registry_tool("web_search"),
                    registry_tool("fetch_as_markdown"),
                    registry_tool("get_weather"),
                ],
            }
            code_executor_agent = {
                "name": "code-executor",
                "description": "Use for editing repository files, running shell commands, and applying patches.",
                "system_prompt": CODE_EXECUTOR_SUBAGENT_PROMPT,
                "tools": [
                    list_directory_tool,
                    registry_tool("tree_view"),
                    read_file_tool,
                    write_file_tool,
                    copy_file_tool,
                    move_file_tool,
                    delete_file_tool,
                    file_search_tool,
                    registry_tool("multi_replace_in_file"),
                    registry_tool("apply_patch"),
                    registry_tool("grep_search"),
                    registry_tool("read_files_in_directory"),
                    registry_tool("shell"),
                    registry_tool("os_info"),
                ],
            }
            greeting_agent = {
                "name": "greeting-responder",
                "description": "Use for crafting friendly greetings, jokes, and casual replies.",
                "system_prompt": "You are a witty greeter. Respond with short, friendly greetings, optionally including light jokes.",
                "tools": [],
            }
            return [
                greeting_agent,
                research_agent,
                {
                    **research_agent,
                    "name": "web-research-analyst",
                },
                code_executor_agent,
                {
                    **code_executor_agent,
                    "name": "code-executor",
                },
            ]

        import os
        from langchain_ollama import ChatOllama
        from langchain_openai import ChatOpenAI

        def get_llm():
            provider = os.environ.get("LLM_PROVIDER", "openai").lower()

            if provider == "ollama":
                return ChatOllama(
                    model=os.environ.get("OLLAMA_MODEL", "qwen3:latest"),
                    base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
                    temperature=0.7,
                    streaming=True,
                )

            api_key = os.environ.get("GLM_API_KEY")
            api_base = os.environ.get("GLM_API_BASE", "https://api.z.ai/api/paas/v4/")

            return ChatOpenAI(
                temperature=0.7,
                model="glm-4.5-flash",
                openai_api_key=api_key,
                openai_api_base=api_base,
                max_retries=30,
                streaming=True,
            )

        llm = get_llm()

        LANGGRAPH_PLATFORM_ENV_KEYS = {
            "LANGGRAPH_API_BASE",
            "LANGGRAPH_API_KEY",
            "LANGGRAPH_PROJECT_ID",
            "LANGGRAPH_CLOUD",
            "LANGGRAPH_DEPLOYMENT",
            "LANGGRAPH_GATEWAY_URL",
            "LANGGRAPH_PLATFORM",
        }

        def should_use_custom_checkpointer() -> bool:
            flag = os.environ.get("DISABLE_CUSTOM_CHECKPOINTER")
            if flag and flag.lower() in {"1", "true", "yes"}:
                return False
            return not any(os.environ.get(key) for key in LANGGRAPH_PLATFORM_ENV_KEYS)

        agent_kwargs = {
            "model": llm,
            "tools": ALL_BASE_TOOLS,
            "system_prompt": SYSTEM_PROMPT,
            "subagents": build_subagents(),
            "interrupt_on": {
                "file_delete": {"allowed_decisions": ["approve", "edit", "reject"]},
                "shell": {"allowed_decisions": ["approve", "edit", "reject"]},
                "write_file": {"allowed_decisions": ["approve", "edit", "reject"]},
                "copy_file": {"allowed_decisions": ["approve", "edit", "reject"]},
                "move_file": {"allowed_decisions": ["approve", "edit", "reject"]},
                "apply_patch": {"allowed_decisions": ["approve", "edit", "reject"]},
                "multi_replace_in_file": {"allowed_decisions": ["approve", "edit", "reject"]},
                "critical_operation": {"allowed_decisions": ["approve"]},
            },
        }

        if should_use_custom_checkpointer():
            cp_config = self.config.checkpointer_config
            if cp_config:
                agent_kwargs["checkpointer"] = create_checkpointer(cp_config)
            else:
                agent_kwargs["checkpointer"] = create_checkpointer()

        return _create_deep_agent(**agent_kwargs)

    async def _emit_hook(self, event: LifecycleEvent, **kwargs) -> None:
        """Emit a lifecycle hook event if hooks are available.

        Args:
            event: The lifecycle event type
            **kwargs: Context fields to include
        """
        if self._emitter and _HOOKS_AVAILABLE:
            try:
                await self._emitter.emit(event, **kwargs)
            except Exception as e:
                logger.warning(f"Hook emit error for {event}: {e}")

    def run(self, task: str, **kwargs) -> Any:
        """Run the agent on a task.

        Args:
            task: Task description to execute
            **kwargs: Additional context for the task

        Returns:
            Result from the agent execution
        """
        return self._app.invoke({"task": task, **kwargs})

    async def run_async(self, task: str, **kwargs) -> Any:
        """Run the agent on a task asynchronously.

        Args:
            task: Task description to execute
            **kwargs: Additional context for the task

        Returns:
            Result from the agent execution
        """
        return await self._app.ainvoke({"task": task, **kwargs})

    def get_evaluator(self) -> EvaluatorAgent | None:
        """Get the evaluator agent if available."""
        return self._evaluator

    def get_planner(self) -> PlannerAgent | None:
        """Get the planner agent if available."""
        return self._planner

    def get_live_verifier(self) -> LiveVerifier | None:
        """Get the live verifier if available."""
        return self._live_verifier

    def get_metrics(self) -> HarnessMetrics | None:
        """Get the metrics collector if available."""
        return self._metrics

    @property
    def app(self):
        """Access the underlying deepagents app."""
        return self._app

    @property
    def is_initialized(self) -> bool:
        """Check if the agent is fully initialized."""
        return getattr(self, "_initialized", False)


def create_deep_agent(config: DeepAgentConfig | None = None) -> DeepAgent:
    """Factory function to create a DeepAgent instance.

    Args:
        config: Optional DeepAgentConfig instance

    Returns:
        Configured DeepAgent instance
    """
    return DeepAgent(config=config)


# Module-level exports for CLI compatibility
# main.py imports `app` and `agent_kwargs` from this module
# We use a class wrapper to defer full initialization until first access


class _LazyExport:
    """Lazy loader that defers DeepAgent creation until first attribute access."""

    _instance = None

    def __getattr__(self, name):
        if _LazyExport._instance is None:
            _LazyExport._instance = create_deep_agent()
        return getattr(_LazyExport._instance, name)


class _LazyApp:
    """Lazy app wrapper that creates DeepAgent on first use."""

    _app = None

    def __getattr__(self, attr):
        if _LazyApp._app is None:
            _LazyApp._app = create_deep_agent()._app
        return getattr(_LazyApp._app, attr)


# Module-level exports for CLI compatibility
# main.py imports `app` and `agent_kwargs` from this module
# app is lazily initialized on first attribute access
# agent_kwargs is set up for CLI re-creation path
app = _LazyApp()
agent_kwargs = {}
