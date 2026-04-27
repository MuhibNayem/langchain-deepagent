"""Test suite with 100+ benchmark test cases.

Each test case has known correct answer or scoring criteria for
automated evaluation of the LuminaMind agent.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class TaskCategory(Enum):
    """Categories of tasks for benchmark testing."""

    CODE_GEN = "code_generation"
    DEBUGGING = "debugging"
    REFACTORING = "refactoring"
    DOCUMENTATION = "documentation"
    UI_DESIGN = "ui_design"
    API_DESIGN = "api_design"
    REVIEW = "review"
    OPTIMIZATION = "optimization"


@dataclass
class TestCase:
    """A single test case for benchmarking.

    Attributes:
        id: Unique identifier for the test case
        name: Human-readable name
        category: Task category
        task: The task description/prompt
        expected_output: Expected result or behavior
        scoring_criteria: Function that scores the output (returns 0.0-1.0)
        difficulty: Difficulty level (easy, medium, hard, expert)
    """

    id: str
    name: str
    category: TaskCategory
    task: str
    expected_output: str | None = None
    scoring_criteria: Callable[[str], float] | None = None
    difficulty: str = "medium"

    def score(self, output: str) -> float:
        """Score an output against this test case.

        Args:
            output: The agent's output to score

        Returns:
            Score from 0.0 to 1.0
        """
        if self.scoring_criteria is not None:
            return self.scoring_criteria(output)
        if self.expected_output is not None:
            return self._default_scoring(output)
        return 0.5  # Neutral score if no criteria

    def _default_scoring(self, output: str) -> float:
        """Default scoring based on expected output matching.

        Args:
            output: The output to score

        Returns:
            Score 0.0-1.0 based on matching
        """
        if not output:
            return 0.0
        expected = self.expected_output.lower()
        actual = output.lower()
        if expected == actual:
            return 1.0
        # Partial matching based on common words
        expected_words = set(expected.split())
        actual_words = set(actual.split())
        if not expected_words:
            return 0.5
        overlap = len(expected_words & actual_words)
        return overlap / len(expected_words)


class TestSuite:
    """Collection of test cases organized by category and difficulty.

    Provides filtering, sampling, and management utilities for
    the benchmark test suite.
    """

    def __init__(self) -> None:
        self.cases: list[TestCase] = []
        self._initialize_default_cases()

    def add_case(self, case: TestCase) -> None:
        """Add a test case to the suite.

        Args:
            case: TestCase to add
        """
        self.cases.append(case)

    def get_by_category(self, category: TaskCategory) -> list[TestCase]:
        """Get all test cases in a category.

        Args:
            category: Category to filter by

        Returns:
            List of TestCase in the category
        """
        return [c for c in self.cases if c.category == category]

    def get_by_difficulty(self, difficulty: str) -> list[TestCase]:
        """Get all test cases of a difficulty level.

        Args:
            difficulty: Difficulty level (easy, medium, hard, expert)

        Returns:
            List of TestCase with the difficulty
        """
        return [c for c in self.cases if c.difficulty == difficulty]

    def sample(self, n: int, **kwargs) -> list[TestCase]:
        """Get a random sample of test cases.

        Args:
            n: Number of cases to sample
            **kwargs: Optional filters (category, difficulty)

        Returns:
            List of sampled TestCase
        """
        filtered = self.cases
        if "category" in kwargs:
            filtered = [c for c in filtered if c.category == kwargs["category"]]
        if "difficulty" in kwargs:
            filtered = [c for c in filtered if c.difficulty == kwargs["difficulty"]]
        return random.sample(filtered, min(n, len(filtered)))

    def _initialize_default_cases(self) -> None:
        """Initialize the default test suite with 100+ cases."""
        self.cases = [
            # CODE_GEN cases (20+)
            TestCase(
                id="code_gen_001",
                name="Parse JSON with error handling",
                category=TaskCategory.CODE_GEN,
                task="Write a function that parses JSON and handles invalid input gracefully",
                expected_output="function parse_json(input) { try { return JSON.parse(input); } catch (e) { return null; } }",
                difficulty="easy",
            ),
            TestCase(
                id="code_gen_002",
                name="Binary search implementation",
                category=TaskCategory.CODE_GEN,
                task="Implement a binary search algorithm",
                expected_output="function binarySearch(arr, target) { let left = 0, right = arr.length - 1; while (left <= right) { let mid = Math.floor((left + right) / 2); if (arr[mid] === target) return mid; if (arr[mid] < target) left = mid + 1; else right = mid - 1; } return -1; }",
                difficulty="medium",
            ),
            TestCase(
                id="code_gen_003",
                name="Debounce function",
                category=TaskCategory.CODE_GEN,
                task="Create a debounce function in JavaScript",
                expected_output="function debounce(fn, delay) { let timeoutId; return function(...args) { clearTimeout(timeoutId); timeoutId = setTimeout(() => fn.apply(this, args), delay); }; }",
                difficulty="medium",
            ),
            TestCase(
                id="code_gen_004",
                name="Deep merge objects",
                category=TaskCategory.CODE_GEN,
                task="Write a function that deeply merges two objects",
                expected_output="function deepMerge(target, source) { const result = {...target}; for (const key in source) { if (source[key] && typeof source[key] === 'object') { result[key] = deepMerge(target[key] || {}, source[key]); } else { result[key] = source[key]; } } return result; }",
                difficulty="hard",
            ),
            TestCase(
                id="code_gen_005",
                name="LRU Cache",
                category=TaskCategory.CODE_GEN,
                task="Implement an LRU cache with O(1) get and put",
                expected_output="class LRUCache { constructor(capacity) { this.capacity = capacity; this.cache = new Map(); } get(key) { if (!this.cache.has(key)) return -1; const v = this.cache.get(key); this.cache.delete(key); this.cache.set(key, v); return v; } put(key, value) { if (this.cache.has(key)) this.cache.delete(key); else if (this.cache.size >= this.capacity) { const firstKey = this.cache.keys().next().value; this.cache.delete(firstKey); } this.cache.set(key, value); } }",
                difficulty="expert",
            ),
            TestCase(
                id="code_gen_006",
                name="Async retry with backoff",
                category=TaskCategory.CODE_GEN,
                task="Write an async function that retries with exponential backoff",
                expected_output="async function retryWithBackoff(fn, maxRetries = 3, baseDelay = 1000) { for (let i = 0; i < maxRetries; i++) { try { return await fn(); } catch (e) { if (i === maxRetries - 1) throw e; await new Promise(r => setTimeout(r, baseDelay * Math.pow(2, i))); } } }",
                difficulty="hard",
            ),
            TestCase(
                id="code_gen_007",
                name="Event emitter",
                category=TaskCategory.CODE_GEN,
                task="Implement a simple event emitter in JavaScript",
                expected_output="class EventEmitter { constructor() { this.events = {}; } on(event, listener) { if (!this.events[event]) this.events[event] = []; this.events[event].push(listener); } emit(event, ...args) { if (this.events[event]) this.events[event].forEach(l => l(...args)); } off(event, listener) { if (this.events[event]) this.events[event] = this.events[event].filter(l => l !== listener); } }",
                difficulty="medium",
            ),
            TestCase(
                id="code_gen_008",
                name="Flatten nested array",
                category=TaskCategory.CODE_GEN,
                task="Write a function to flatten a nested array to any depth",
                expected_output="function flatten(arr) { return arr.reduce((acc, val) => Array.isArray(val) ? acc.concat(flatten(val)) : acc.concat(val), []); }",
                difficulty="easy",
            ),
            TestCase(
                id="code_gen_009",
                name="Throttle function",
                category=TaskCategory.CODE_GEN,
                task="Create a throttle function that limits how often a function can be called",
                expected_output="function throttle(fn, limit) { let inThrottle; return function(...args) { if (!inThrottle) { fn.apply(this, args); inThrottle = true; setTimeout(() => inThrottle = false, limit); } }; }",
                difficulty="medium",
            ),
            TestCase(
                id="code_gen_010",
                name="Compose functions",
                category=TaskCategory.CODE_GEN,
                task="Implement a compose function that chains multiple functions",
                expected_output="const compose = (...fns) => x => fns.reduceRight((v, f) => f(v), x);",
                difficulty="medium",
            ),
            # DEBUGGING cases (15+)
            TestCase(
                id="debug_001",
                name="Fix race condition in counter",
                category=TaskCategory.DEBUGGING,
                task="Fix the race condition in this thread-unsafe counter: let count = 0; function increment() { count++; }",
                expected_output="atomic counter or lock mechanism",
                scoring_criteria=lambda o: 1.0 if any(x in o.lower() for x in ["lock", "atomic", "mutex", "synchroniz", "+= 1"]) else 0.0,
                difficulty="hard",
            ),
            TestCase(
                id="debug_002",
                name="Fix memory leak",
                category=TaskCategory.DEBUGGING,
                task="Fix this memory leak: function createHandlers() { let handlers = []; for (let i = 0; i < 100; i++) { handlers.push(() => console.log(i)); } return handlers; }",
                expected_output="closure with let i instead of var",
                scoring_criteria=lambda o: 1.0 if ("let" in o and "var" not in o) or "closure" in o.lower() else 0.0,
                difficulty="medium",
            ),
            TestCase(
                id="debug_003",
                name="Fix async/await error handling",
                category=TaskCategory.DEBUGGING,
                task="Fix this code that silently ignores errors: async function fetchData() { try { return await getData(); } catch (e) { console.log(e); } }",
                expected_output="proper error propagation or logging",
                scoring_criteria=lambda o: 1.0 if "throw" in o or ("catch" in o and "return" not in o.split("catch")[1].split("\n")[0]) else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="debug_004",
                name="Fix null reference",
                category=TaskCategory.DEBUGGING,
                task="Fix the null reference error: const name = user.profile.name;",
                expected_output="optional chaining or null check",
                scoring_criteria=lambda o: 1.0 if "?." in o or "if" in o else 0.0,
                difficulty="easy",
            ),
            TestCase(
                id="debug_005",
                name="Fix array index out of bounds",
                category=TaskCategory.DEBUGGING,
                task="Fix array out of bounds: for (let i = 0; i <= arr.length; i++) console.log(arr[i]);",
                expected_output="i < arr.length not i <= arr.length",
                scoring_criteria=lambda o: 1.0 if "i <" in o and "i <=" not in o.replace("!=", "") else 0.0,
                difficulty="easy",
            ),
            TestCase(
                id="debug_006",
                name="Fix closure in loop",
                category=TaskCategory.DEBUGGING,
                task="Fix this closure problem: for (var i = 0; i < 3; i++) { setTimeout(() => console.log(i), 100); }",
                expected_output="use let instead of var",
                scoring_criteria=lambda o: 1.0 if "let" in o and "var" not in o else 0.0,
                difficulty="easy",
            ),
            TestCase(
                id="debug_007",
                name="Fix promise chain error",
                category=TaskCategory.DEBUGGING,
                task="Fix this promise that never resolves: function wait() { return new Promise(resolve => {}); }",
                expected_output="call resolve() or reject()",
                scoring_criteria=lambda o: 1.0 if "resolve(" in o or "reject(" in o else 0.0,
                difficulty="medium",
            ),
            TestCase(
                id="debug_008",
                name="Fix floating point comparison",
                category=TaskCategory.DEBUGGING,
                task="Fix this floating point comparison: if (0.1 + 0.2 === 0.3) console.log('equal');",
                expected_output="epsilon comparison or tofixed",
                scoring_criteria=lambda o: 1.0 if any(x in o.lower() for x in ["epsilon", "tolerance", "nearly", "approx"]) else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="debug_009",
                name="Fix callback hell",
                category=TaskCategory.DEBUGGING,
                task="Refactor this callback hell to use async/await",
                expected_output="async/await pattern",
                scoring_criteria=lambda o: 1.0 if "await" in o else 0.0,
                difficulty="medium",
            ),
            TestCase(
                id="debug_010",
                name="Fix object mutation",
                category=TaskCategory.DEBUGGING,
                task="Fix this function that mutates its input: function addItem(arr, item) { arr.push(item); return arr; }",
                expected_output="spread or slice to avoid mutation",
                scoring_criteria=lambda o: 1.0 if ("[..." in o or ".slice" in o) and "push" not in o.split("return")[1] else 0.0,
                difficulty="easy",
            ),
            # REFACTORING cases (15+)
            TestCase(
                id="refactor_001",
                name="Extract method",
                category=TaskCategory.REFACTORING,
                task="Extract this long method into smaller pieces",
                expected_output="multiple smaller methods",
                scoring_criteria=lambda o: 1.0 if o.count("function") > 1 or "def " in o else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="refactor_002",
                name="Replace conditional with polymorphism",
                category=TaskCategory.REFACTORING,
                task="Replace this switch statement with a strategy pattern",
                expected_output="class/interface based strategy",
                scoring_criteria=lambda o: 1.0 if "class" in o and ("strategy" in o.lower() or "interface" in o.lower()) else 0.5,
                difficulty="hard",
            ),
            TestCase(
                id="refactor_003",
                name="Remove dead code",
                category=TaskCategory.REFACTORING,
                task="Remove all dead code from this file",
                expected_output="no unreachable code",
                scoring_criteria=lambda o: 0.5 if len(o) < 1000 else 0.3,
                difficulty="easy",
            ),
            TestCase(
                id="refactor_004",
                name="Inline method",
                category=TaskCategory.REFACTORING,
                task="Inline this trivial getter method",
                expected_output="direct property access",
                scoring_criteria=lambda o: 1.0 if "return this." in o or "return " in o else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="refactor_005",
                name="Introduce parameter object",
                category=TaskCategory.REFACTORING,
                task="Replace this long parameter list with a parameter object",
                expected_output="parameter object class",
                scoring_criteria=lambda o: 1.0 if "class" in o and ("param" in o.lower() or "options" in o.lower() or "config" in o.lower()) else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="refactor_006",
                name="Replace magic numbers",
                category=TaskCategory.REFACTORING,
                task="Replace all magic numbers with named constants",
                expected_output="const variables",
                scoring_criteria=lambda o: 1.0 if "const" in o or "MAX" in o or "LIMIT" in o else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="refactor_007",
                name="Extract constant",
                category=TaskCategory.REFACTORING,
                task="Extract hardcoded strings to constants",
                expected_output="const for strings",
                scoring_criteria=lambda o: 1.0 if "const" in o and '"' in o else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="refactor_008",
                name="Rename long variable",
                category=TaskCategory.REFACTORING,
                task="Rename this unclear variable name",
                expected_output="descriptive name",
                scoring_criteria=lambda o: 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="refactor_009",
                name="Simplify complex condition",
                category=TaskCategory.REFACTORING,
                task="Simplify this nested if statement",
                expected_output="simplified logic",
                scoring_criteria=lambda o: 0.5 if o.count("if") < 4 else 0.3,
                difficulty="medium",
            ),
            TestCase(
                id="refactor_010",
                name="Convert to arrow functions",
                category=TaskCategory.REFACTORING,
                task="Convert function expressions to arrow functions",
                expected_output="=> syntax",
                scoring_criteria=lambda o: 1.0 if "=>" in o else 0.0,
                difficulty="easy",
            ),
            # DOCUMENTATION cases (10+)
            TestCase(
                id="docs_001",
                name="Document API endpoint",
                category=TaskCategory.DOCUMENTATION,
                task="Write OpenAPI documentation for a user endpoint",
                expected_output="swagger/openapi spec",
                scoring_criteria=lambda o: 1.0 if "openapi" in o.lower() or "swagger" in o.lower() or "endpoint" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="docs_002",
                name="Write README",
                category=TaskCategory.DOCUMENTATION,
                task="Write a README for a Node.js project",
                expected_output="markdown with installation and usage",
                scoring_criteria=lambda o: 1.0 if "# " in o and "install" in o.lower() else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="docs_003",
                name="Document function with JSDoc",
                category=TaskCategory.DOCUMENTATION,
                task="Add JSDoc comments to this function",
                expected_output="/** comments */",
                scoring_criteria=lambda o: 1.0 if "/**" in o else 0.0,
                difficulty="easy",
            ),
            TestCase(
                id="docs_004",
                name="Write changelog entry",
                category=TaskCategory.DOCUMENTATION,
                task="Write a changelog entry for version 1.2.0",
                expected_output="version and date format",
                scoring_criteria=lambda o: 1.0 if "1.2.0" in o or "1.2" in o else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="docs_005",
                name="Document class interface",
                category=TaskCategory.DOCUMENTATION,
                task="Write TypeScript interface documentation",
                expected_output="interface declaration",
                scoring_criteria=lambda o: 1.0 if "interface" in o else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="docs_006",
                name="Create architecture doc",
                category=TaskCategory.DOCUMENTATION,
                task="Document the system architecture",
                expected_output="diagram and components",
                scoring_criteria=lambda o: 0.5,
                difficulty="hard",
            ),
            TestCase(
                id="docs_007",
                name="Write migration guide",
                category=TaskCategory.DOCUMENTATION,
                task="Write a migration guide from v1 to v2",
                expected_output="step by step instructions",
                scoring_criteria=lambda o: 1.0 if "step" in o.lower() or "guide" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="docs_008",
                name="Document error codes",
                category=TaskCategory.DOCUMENTATION,
                task="Document all error codes for the API",
                expected_output="error code list with descriptions",
                scoring_criteria=lambda o: 1.0 if "error" in o.lower() and "code" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="docs_009",
                name="Write contributing guide",
                category=TaskCategory.DOCUMENTATION,
                task="Write a contributing guidelines document",
                expected_output="CONTRIBUTING.md style",
                scoring_criteria=lambda o: 1.0 if "pull" in o.lower() and "request" in o.lower() else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="docs_010",
                name="Document config schema",
                category=TaskCategory.DOCUMENTATION,
                task="Document the config.yaml schema",
                expected_output="yaml structure with descriptions",
                scoring_criteria=lambda o: 1.0 if ":" in o and "#" in o else 0.5,
                difficulty="medium",
            ),
            # UI_DESIGN cases (10+)
            TestCase(
                id="ui_001",
                name="Login form with validation",
                category=TaskCategory.UI_DESIGN,
                task="Create a login form with field validation",
                expected_output="form with validation",
                scoring_criteria=lambda o: 1.0 if "form" in o.lower() and ("valid" in o.lower() or "email" in o.lower() or "password" in o.lower()) else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="ui_002",
                name="Responsive grid layout",
                category=TaskCategory.UI_DESIGN,
                task="Design a responsive grid layout for dashboard",
                expected_output="grid or flexbox layout",
                scoring_criteria=lambda o: 1.0 if "grid" in o.lower() or "flex" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="ui_003",
                name="Modal dialog component",
                category=TaskCategory.UI_DESIGN,
                task="Create a modal dialog component with backdrop",
                expected_output="modal with overlay",
                scoring_criteria=lambda o: 1.0 if "modal" in o.lower() or "dialog" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="ui_004",
                name="Navigation sidebar",
                category=TaskCategory.UI_DESIGN,
                task="Build a collapsible navigation sidebar",
                expected_output="sidebar with toggle",
                scoring_criteria=lambda o: 1.0 if "nav" in o.lower() or "sidebar" in o.lower() else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="ui_005",
                name="Data table with sorting",
                category=TaskCategory.UI_DESIGN,
                task="Design a data table with column sorting",
                expected_output="table with sort indicators",
                scoring_criteria=lambda o: 1.0 if "table" in o.lower() and "sort" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="ui_006",
                name="Toast notification",
                category=TaskCategory.UI_DESIGN,
                task="Create a toast notification system",
                expected_output="toast component",
                scoring_criteria=lambda o: 1.0 if "toast" in o.lower() or "notification" in o.lower() else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="ui_007",
                name="Loading spinner",
                category=TaskCategory.UI_DESIGN,
                task="Design a loading spinner component",
                expected_output="spinner animation",
                scoring_criteria=lambda o: 1.0 if "spin" in o.lower() or "load" in o.lower() or "@keyframes" in o else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="ui_008",
                name="Card component",
                category=TaskCategory.UI_DESIGN,
                task="Create a card component with shadow",
                expected_output="card with shadow",
                scoring_criteria=lambda o: 1.0 if "card" in o.lower() and ("shadow" in o.lower() or "box-shadow" in o) else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="ui_009",
                name="Dropdown select",
                category=TaskCategory.UI_DESIGN,
                task="Build a custom dropdown select component",
                expected_output="dropdown with options",
                scoring_criteria=lambda o: 1.0 if "dropdown" in o.lower() or "select" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="ui_010",
                name="Tab navigation",
                category=TaskCategory.UI_DESIGN,
                task="Create tab navigation component",
                expected_output="tabs with active state",
                scoring_criteria=lambda o: 1.0 if "tab" in o.lower() and "active" in o.lower() else 0.5,
                difficulty="easy",
            ),
            # API_DESIGN cases (10+)
            TestCase(
                id="api_001",
                name="RESTful user CRUD",
                category=TaskCategory.API_DESIGN,
                task="Design RESTful endpoints for user management",
                expected_output="GET/POST/PUT/DELETE endpoints",
                scoring_criteria=lambda o: 1.0 if "get" in o.lower() and "post" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="api_002",
                name="Pagination parameters",
                category=TaskCategory.API_DESIGN,
                task="Design paginated list endpoint with cursor",
                expected_output="limit and cursor params",
                scoring_criteria=lambda o: 1.0 if "cursor" in o.lower() or ("limit" in o.lower() and "offset" in o.lower()) else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="api_003",
                name="Error response format",
                category=TaskCategory.API_DESIGN,
                task="Design a consistent error response format",
                expected_output="error object with code and message",
                scoring_criteria=lambda o: 1.0 if "error" in o.lower() and ("code" in o.lower() or "message" in o.lower()) else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="api_004",
                name="Authentication headers",
                category=TaskCategory.API_DESIGN,
                task="Design authentication headers for API",
                expected_output="authorization header",
                scoring_criteria=lambda o: 1.0 if "authorization" in o.lower() or "bearer" in o.lower() else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="api_005",
                name="Webhook payload",
                category=TaskCategory.API_DESIGN,
                task="Design webhook payload structure",
                expected_output="event and data fields",
                scoring_criteria=lambda o: 1.0 if "event" in o.lower() and "payload" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="api_006",
                name="Rate limiting headers",
                category=TaskCategory.API_DESIGN,
                task="Design rate limiting response headers",
                expected_output="X-RateLimit headers",
                scoring_criteria=lambda o: 1.0 if "ratelimit" in o.lower() or "limit" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="api_007",
                name="GraphQL schema",
                category=TaskCategory.API_DESIGN,
                task="Design a GraphQL schema for a blog",
                expected_output="type definitions",
                scoring_criteria=lambda o: 1.0 if "type" in o.lower() and "query" in o.lower() else 0.5,
                difficulty="hard",
            ),
            TestCase(
                id="api_008",
                name="API versioning",
                category=TaskCategory.API_DESIGN,
                task="Design versioned API endpoints",
                expected_output="/v1/ prefix",
                scoring_criteria=lambda o: 1.0 if "/v1" in o or "/v2" in o else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="api_009",
                name="File upload endpoint",
                category=TaskCategory.API_DESIGN,
                task="Design a file upload endpoint",
                expected_output="multipart/form-data",
                scoring_criteria=lambda o: 1.0 if "multipart" in o.lower() or "upload" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="api_010",
                name="Search API",
                category=TaskCategory.API_DESIGN,
                task="Design a search endpoint with filters",
                expected_output="q param and filters",
                scoring_criteria=lambda o: 1.0 if "search" in o.lower() or "q=" in o or "query" in o.lower() else 0.5,
                difficulty="easy",
            ),
            # REVIEW cases (10+)
            TestCase(
                id="review_001",
                name="Security: SQL injection",
                category=TaskCategory.REVIEW,
                task="Review this code for SQL injection vulnerabilities",
                expected_output="parameterized queries",
                scoring_criteria=lambda o: 1.0 if "param" in o.lower() or "injection" in o.lower() or "sanitiz" in o.lower() else 0.5,
                difficulty="hard",
            ),
            TestCase(
                id="review_002",
                name="Performance: N+1 query",
                category=TaskCategory.REVIEW,
                task="Review this code for N+1 query problems",
                expected_output="batch query or join",
                scoring_criteria=lambda o: 1.0 if "batch" in o.lower() or "join" in o.lower() or "n+1" in o.lower() else 0.5,
                difficulty="hard",
            ),
            TestCase(
                id="review_003",
                name="Code style: naming",
                category=TaskCategory.REVIEW,
                task="Review variable naming conventions",
                expected_output="snake_case or camelCase",
                scoring_criteria=lambda o: 1.0 if "naming" in o.lower() or "convention" in o.lower() else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="review_004",
                name="Accessibility audit",
                category=TaskCategory.REVIEW,
                task="Review this UI for accessibility issues",
                expected_output="aria labels and keyboard nav",
                scoring_criteria=lambda o: 1.0 if "aria" in o.lower() or "accessibility" in o.lower() or "a11y" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="review_005",
                name="Error handling review",
                category=TaskCategory.REVIEW,
                task="Review error handling patterns",
                expected_output="try/catch or error boundaries",
                scoring_criteria=lambda o: 1.0 if "error" in o.lower() and ("handle" in o.lower() or "catch" in o.lower()) else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="review_006",
                name="Dependency audit",
                category=TaskCategory.REVIEW,
                task="Audit dependencies for security vulnerabilities",
                expected_output="audit report or update recommendations",
                scoring_criteria=lambda o: 1.0 if "audit" in o.lower() or "vulnerab" in o.lower() or "security" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="review_007",
                name="API contract review",
                category=TaskCategory.REVIEW,
                task="Review API contract for breaking changes",
                expected_output="backward compatibility notes",
                scoring_criteria=lambda o: 1.0 if "compatible" in o.lower() or "breaking" in o.lower() or "version" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="review_008",
                name="Test coverage review",
                category=TaskCategory.REVIEW,
                task="Review test coverage for missing cases",
                expected_output="coverage report or missing tests",
                scoring_criteria=lambda o: 1.0 if "coverage" in o.lower() or "test" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="review_009",
                name="Logging audit",
                category=TaskCategory.REVIEW,
                task="Review logging strategy for production",
                expected_output="structured logging recommendations",
                scoring_criteria=lambda o: 1.0 if "log" in o.lower() and ("structured" in o.lower() or "level" in o.lower()) else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="review_010",
                name="Type safety review",
                category=TaskCategory.REVIEW,
                task="Review code for type safety issues",
                expected_output="TypeScript or type hints",
                scoring_criteria=lambda o: 1.0 if "type" in o.lower() and ("safety" in o.lower() or "strict" in o.lower()) else 0.5,
                difficulty="medium",
            ),
            # OPTIMIZATION cases (10+)
            TestCase(
                id="opt_001",
                name="Memoization",
                category=TaskCategory.OPTIMIZATION,
                task="Add memoization to this expensive function",
                expected_output="cache or memo decorator",
                scoring_criteria=lambda o: 1.0 if "memo" in o.lower() or "cache" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="opt_002",
                name="Lazy loading",
                category=TaskCategory.OPTIMIZATION,
                task="Implement lazy loading for images",
                expected_output="loading='lazy' or IntersectionObserver",
                scoring_criteria=lambda o: 1.0 if "lazy" in o.lower() or "intersection" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="opt_003",
                name="Batch DOM updates",
                category=TaskCategory.OPTIMIZATION,
                task="Batch these DOM updates together",
                expected_output="DocumentFragment or requestAnimationFrame",
                scoring_criteria=lambda o: 1.0 if "fragment" in o.lower() or "batch" in o.lower() or "requestAnimationFrame" in o else 0.5,
                difficulty="hard",
            ),
            TestCase(
                id="opt_004",
                name="Index database query",
                category=TaskCategory.OPTIMIZATION,
                task="Add index to optimize this slow query",
                expected_output="CREATE INDEX",
                scoring_criteria=lambda o: 1.0 if "index" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="opt_005",
                name="Compress images",
                category=TaskCategory.OPTIMIZATION,
                task="Suggest image compression strategy",
                expected_output="compression format or lazy loading",
                scoring_criteria=lambda o: 1.0 if "compress" in o.lower() or "webp" in o.lower() or "avif" in o.lower() else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="opt_006",
                name="Debounce scroll handler",
                category=TaskCategory.OPTIMIZATION,
                task="Optimize scroll event handler",
                expected_output="throttle or debounce",
                scoring_criteria=lambda o: 1.0 if "throttle" in o.lower() or "debounce" in o.lower() else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="opt_007",
                name="Virtualize long list",
                category=TaskCategory.OPTIMIZATION,
                task="Virtualize this long list for performance",
                expected_output="virtual list or windowing",
                scoring_criteria=lambda o: 1.0 if "virtual" in o.lower() or "window" in o.lower() or "recycl" in o.lower() else 0.5,
                difficulty="hard",
            ),
            TestCase(
                id="opt_008",
                name="Cache API responses",
                category=TaskCategory.OPTIMIZATION,
                task="Implement API response caching",
                expected_output="cache storage or headers",
                scoring_criteria=lambda o: 1.0 if "cache" in o.lower() or "Expires" in o or "max-age" in o else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="opt_009",
                name="Code splitting",
                category=TaskCategory.OPTIMIZATION,
                task="Suggest code splitting strategy",
                expected_output="dynamic import",
                scoring_criteria=lambda o: 1.0 if "split" in o.lower() or "dynamic" in o.lower() or "import" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="opt_010",
                name="Prefetch resources",
                category=TaskCategory.OPTIMIZATION,
                task="Add resource prefetching for navigation",
                expected_output="<link prefetch>",
                scoring_criteria=lambda o: 1.0 if "prefetch" in o.lower() or "preload" in o.lower() else 0.5,
                difficulty="easy",
            ),
            # Additional CODE_GEN cases (11-15)
            TestCase(
                id="code_gen_011",
                name="Queue implementation",
                category=TaskCategory.CODE_GEN,
                task="Implement a queue data structure with enqueue and dequeue",
                expected_output="queue with add and remove",
                scoring_criteria=lambda o: 1.0 if ("enqueue" in o.lower() or "add" in o.lower()) and ("dequeue" in o.lower() or "remove" in o.lower()) else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="code_gen_012",
                name="Trie data structure",
                category=TaskCategory.CODE_GEN,
                task="Implement a trie (prefix tree) for efficient string operations",
                expected_output="trie class with insert and search",
                scoring_criteria=lambda o: 1.0 if "trie" in o.lower() and ("insert" in o.lower() or "search" in o.lower()) else 0.5,
                difficulty="expert",
            ),
            TestCase(
                id="code_gen_013",
                name="Hash map implementation",
                category=TaskCategory.CODE_GEN,
                task="Implement a hash map with collision handling",
                expected_output="hash map with buckets",
                scoring_criteria=lambda o: 1.0 if "hash" in o.lower() and ("map" in o.lower() or "bucket" in o.lower()) else 0.5,
                difficulty="hard",
            ),
            TestCase(
                id="code_gen_014",
                name="Singleton pattern",
                category=TaskCategory.CODE_GEN,
                task="Implement thread-safe singleton pattern",
                expected_output="singleton with double-checked locking",
                scoring_criteria=lambda o: 1.0 if "singleton" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="code_gen_015",
                name="Curry function",
                category=TaskCategory.CODE_GEN,
                task="Implement a curry function that partially applies arguments",
                expected_output="curry function returning function",
                scoring_criteria=lambda o: 1.0 if "curry" in o.lower() or ("return" in o and "function" in o) else 0.5,
                difficulty="medium",
            ),
            # Additional DEBUGGING cases (11-15)
            TestCase(
                id="debug_011",
                name="Fix event listener leak",
                category=TaskCategory.DEBUGGING,
                task="Fix this event listener that is not being removed: element.addEventListener('click', handler);",
                expected_output="removeEventListener or cleanup",
                scoring_criteria=lambda o: 1.0 if "remove" in o.lower() or "cleanup" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="debug_012",
                name="Fix hoisting issue",
                category=TaskCategory.DEBUGGING,
                task="Fix this variable hoisting issue with var declarations in loops",
                expected_output="let instead of var",
                scoring_criteria=lambda o: 1.0 if "let" in o and "var" not in o else 0.0,
                difficulty="easy",
            ),
            TestCase(
                id="debug_013",
                name="Fix timezone bug",
                category=TaskCategory.DEBUGGING,
                task="Fix this date handling that doesn't account for timezone",
                expected_output="timezone handling",
                scoring_criteria=lambda o: 1.0 if "timezone" in o.lower() or "UTC" in o or "zoned" in o.lower() else 0.5,
                difficulty="hard",
            ),
            TestCase(
                id="debug_014",
                name="Fix deep clone",
                category=TaskCategory.DEBUGGING,
                task="Fix this shallow clone issue: const copy = {...obj}",
                expected_output="structuredClone or deep copy",
                scoring_criteria=lambda o: 1.0 if "deep" in o.lower() or "structured" in o.lower() or "JSON.parse" in o else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="debug_015",
                name="Fix reduce accumulator",
                category=TaskCategory.DEBUGGING,
                task="Fix this reduce that returns undefined: arr.reduce((acc, item) => { acc.push(item); })",
                expected_output="return acc",
                scoring_criteria=lambda o: 1.0 if "return" in o and "acc" in o else 0.5,
                difficulty="easy",
            ),
            # Additional DOCUMENTATION cases (11-15)
            TestCase(
                id="docs_011",
                name="Document component props",
                category=TaskCategory.DOCUMENTATION,
                task="Write prop documentation for a React component",
                expected_output="prop types and descriptions",
                scoring_criteria=lambda o: 1.0 if "prop" in o.lower() and ("type" in o.lower() or "description" in o.lower()) else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="docs_012",
                name="Create API reference",
                category=TaskCategory.DOCUMENTATION,
                task="Create API reference documentation for a library",
                expected_output="api methods with descriptions",
                scoring_criteria=lambda o: 1.0 if "api" in o.lower() and ("method" in o.lower() or "function" in o.lower()) else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="docs_013",
                name="Write deployment guide",
                category=TaskCategory.DOCUMENTATION,
                task="Write a deployment guide for a web application",
                expected_output="deployment steps and config",
                scoring_criteria=lambda o: 1.0 if "deploy" in o.lower() and ("step" in o.lower() or "config" in o.lower()) else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="docs_014",
                name="Document environment vars",
                category=TaskCategory.DOCUMENTATION,
                task="Document all environment variables for the application",
                expected_output="env vars list with descriptions",
                scoring_criteria=lambda o: 1.0 if "env" in o.lower() and ("variable" in o.lower() or "config" in o.lower()) else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="docs_015",
                name="Write testing guide",
                category=TaskCategory.DOCUMENTATION,
                task="Write a testing strategy document",
                expected_output="testing approach and coverage goals",
                scoring_criteria=lambda o: 1.0 if "test" in o.lower() and ("coverage" in o.lower() or "strategy" in o.lower()) else 0.5,
                difficulty="medium",
            ),
            # Additional UI_DESIGN cases (11-15)
            TestCase(
                id="ui_011",
                name="Color palette system",
                category=TaskCategory.UI_DESIGN,
                task="Design a color palette system with primary, secondary, and accent colors",
                expected_output="CSS variables for colors",
                scoring_criteria=lambda o: 1.0 if "color" in o.lower() and ("primary" in o.lower() or "secondary" in o.lower()) else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="ui_012",
                name="Button variants",
                category=TaskCategory.UI_DESIGN,
                task="Create button component variants (primary, secondary, outline, ghost)",
                expected_output="button styles",
                scoring_criteria=lambda o: 1.0 if "button" in o.lower() and ("primary" in o.lower() or "secondary" in o.lower()) else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="ui_013",
                name="Typography scale",
                category=TaskCategory.UI_DESIGN,
                task="Design a typography scale for headings and body text",
                expected_output="font size scale",
                scoring_criteria=lambda o: 1.0 if "font" in o.lower() and ("size" in o.lower() or "scale" in o.lower()) else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="ui_014",
                name="Form validation states",
                category=TaskCategory.UI_DESIGN,
                task="Design form input states for error, success, and warning",
                expected_output="validation visual feedback",
                scoring_criteria=lambda o: 1.0 if ("error" in o.lower() or "valid" in o.lower()) and "state" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="ui_015",
                name="Responsive breakpoints",
                category=TaskCategory.UI_DESIGN,
                task="Define responsive breakpoints for mobile, tablet, and desktop",
                expected_output="media query breakpoints",
                scoring_criteria=lambda o: 1.0 if "breakpoint" in o.lower() or "media" in o.lower() or "responsive" in o.lower() else 0.5,
                difficulty="easy",
            ),
            # Additional API_DESIGN cases (11-15)
            TestCase(
                id="api_011",
                name="Batch operations endpoint",
                category=TaskCategory.API_DESIGN,
                task="Design an endpoint for batch operations",
                expected_output="batch or bulk endpoint",
                scoring_criteria=lambda o: 1.0 if "batch" in o.lower() or "bulk" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="api_012",
                name="Filter and sort params",
                category=TaskCategory.API_DESIGN,
                task="Design query parameters for filtering and sorting",
                expected_output="filter and sort params",
                scoring_criteria=lambda o: 1.0 if "filter" in o.lower() or "sort" in o.lower() else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="api_013",
                name="Idempotency key",
                category=TaskCategory.API_DESIGN,
                task="Design idempotency key handling for safe retries",
                expected_output="idempotency key header",
                scoring_criteria=lambda o: 1.0 if "idempotency" in o.lower() or "retry" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="api_014",
                name="Field projection",
                category=TaskCategory.API_DESIGN,
                task="Design field selection/projection for sparse datasets",
                expected_output="fields parameter",
                scoring_criteria=lambda o: 1.0 if "field" in o.lower() and ("select" in o.lower() or "project" in o.lower()) else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="api_015",
                name="Async webhooks",
                category=TaskCategory.API_DESIGN,
                task="Design async webhook delivery with retry logic",
                expected_output="webhook with retry",
                scoring_criteria=lambda o: 1.0 if "webhook" in o.lower() and ("retry" in o.lower() or "async" in o.lower()) else 0.5,
                difficulty="hard",
            ),
            # Additional REVIEW cases (11-15)
            TestCase(
                id="review_011",
                name="Circular dependency check",
                category=TaskCategory.REVIEW,
                task="Review code for circular dependencies",
                expected_output="dependency graph analysis",
                scoring_criteria=lambda o: 1.0 if "circular" in o.lower() or "dependency" in o.lower() else 0.5,
                difficulty="hard",
            ),
            TestCase(
                id="review_012",
                name="API rate limit review",
                category=TaskCategory.REVIEW,
                task="Review API endpoints for proper rate limiting",
                expected_output="rate limit implementation",
                scoring_criteria=lambda o: 1.0 if "rate" in o.lower() and "limit" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="review_013",
                name="Secret management",
                category=TaskCategory.REVIEW,
                task="Review secret management in the codebase",
                expected_output="secret rotation or vault",
                scoring_criteria=lambda o: 1.0 if "secret" in o.lower() and ("rotate" in o.lower() or "vault" in o.lower() or "env" in o.lower()) else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="review_014",
                name="Input sanitization",
                category=TaskCategory.REVIEW,
                task="Review input sanitization for XSS prevention",
                expected_output="sanitization or validation",
                scoring_criteria=lambda o: 1.0 if "sanitiz" in o.lower() or "xss" in o.lower() or "escape" in o.lower() else 0.5,
                difficulty="hard",
            ),
            TestCase(
                id="review_015",
                name="Error message security",
                category=TaskCategory.REVIEW,
                task="Review error messages for information leakage",
                expected_output="generic error messages",
                scoring_criteria=lambda o: 1.0 if "error" in o.lower() and ("generic" in o.lower() or "message" in o.lower()) else 0.5,
                difficulty="medium",
            ),
            # Additional OPTIMIZATION cases (11-15)
            TestCase(
                id="opt_011",
                name="CSS containment",
                category=TaskCategory.OPTIMIZATION,
                task="Add CSS containment for layout performance",
                expected_output="contain CSS property",
                scoring_criteria=lambda o: 1.0 if "contain" in o.lower() or "layout" in o.lower() else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="opt_012",
                name="Resource hints",
                category=TaskCategory.OPTIMIZATION,
                task="Add resource hints (dns-prefetch, preconnect) for critical resources",
                expected_output="dns-prefetch or preconnect",
                scoring_criteria=lambda o: 1.0 if "dns-prefetch" in o or "preconnect" in o else 0.5,
                difficulty="easy",
            ),
            TestCase(
                id="opt_013",
                name="Bundle analysis",
                category=TaskCategory.OPTIMIZATION,
                task="Analyze and suggest bundle splitting strategy",
                expected_output="bundle splitting",
                scoring_criteria=lambda o: 1.0 if "bundle" in o.lower() and ("split" in o.lower() or "chunk" in o.lower()) else 0.5,
                difficulty="medium",
            ),
            TestCase(
                id="opt_014",
                name="Database connection pooling",
                category=TaskCategory.OPTIMIZATION,
                task="Implement database connection pooling",
                expected_output="connection pool",
                scoring_criteria=lambda o: 1.0 if "pool" in o.lower() and ("connection" in o.lower() or "database" in o.lower()) else 0.5,
                difficulty="hard",
            ),
            TestCase(
                id="opt_015",
                name="HTTP caching headers",
                category=TaskCategory.OPTIMIZATION,
                task="Configure optimal HTTP caching headers",
                expected_output="cache-control header",
                scoring_criteria=lambda o: 1.0 if "cache-control" in o.lower() or "Expires" in o else 0.5,
                difficulty="easy",
            ),
        ]


def _create_default_suite() -> TestSuite:
    """Create the default test suite."""
    return TestSuite()


# Module-level default suite
default_suite = TestSuite()