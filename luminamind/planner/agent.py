"""PlannerAgent with spec expansion and AI suggestion integration.

Per PLAN-01: Spec in <5 min that evaluator approves.
Per PLAN-02: Structured output with feature decomposition.
"""
import time
import json
import re
from dataclasses import dataclass, field

from luminamind.planner.spec import SpecDocument, UserStory, AcceptanceCriterion
from luminamind.deep_agent import get_llm


@dataclass
class SpecResult:
    """Result of spec generation.

    Attributes:
        spec: The generated SpecDocument
        generation_time_seconds: Time taken to generate
        suggestions: AI-provided alternative decompositions
    """

    spec: SpecDocument
    generation_time_seconds: float
    suggestions: list[str] = field(default_factory=list)


def parse_json_response(content: str) -> dict:
    """Parse JSON from LLM response content.

    Handles markdown code blocks, plain JSON, and malformed JSON.

    Args:
        content: Raw response content from LLM

    Returns:
        Parsed dictionary
    """
    # Strip markdown code blocks if present
    json_str = content
    if "```json" in json_str:
        match = re.search(r"```json\s*(.*?)\s*```", json_str, re.DOTALL)
        if match:
            json_str = match.group(1)
    elif "```" in json_str:
        match = re.search(r"```\s*(.*?)\s*```", json_str, re.DOTALL)
        if match:
            json_str = match.group(1)

    # Try to find JSON object in content
    json_str = json_str.strip()

    # Handle cases where LLM returns text before/after JSON
    if not json_str.startswith("{"):
        # Try to find first {
        idx = json_str.find("{")
        if idx >= 0:
            json_str = json_str[idx:]
        # Try to find last }
        idx = json_str.rfind("}")
        if idx >= 0:
            json_str = json_str[: idx + 1]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # Try to fix common issues
        json_str = json_str.replace("'", '"')
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Return minimal valid structure
            return {"id": "error", "title": "Parse Error", "description": content, "feature_request": ""}


def parse_alternatives(content: str) -> list[str]:
    """Parse alternative decomposition suggestions from LLM response.

    Args:
        content: Raw response content from LLM

    Returns:
        List of suggestion strings
    """
    suggestions = []

    # Try to extract as JSON first
    try:
        if "```json" in content:
            match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and "suggestions" in data:
                    return data["suggestions"]
        elif content.strip().startswith("["):
            return json.loads(content)
    except (json.JSONDecodeError, AttributeError):
        pass

    # Fallback: extract lines that look like suggestions
    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        if line and len(line) > 10:
            # Remove leading bullets, numbers
            cleaned = re.sub(r"^[\d\.\-\*\•]+\s*", "", line)
            if cleaned:
                suggestions.append(cleaned)

    return suggestions[:3]  # Limit to 3 suggestions


class PlannerAgent:
    """Agent that generates structured specs from feature requests.

    Uses AI decomposition to break features into user stories with acceptance
    criteria. Generates specs in <5 min that can be reviewed by evaluator.

    Attributes:
        model: LLM to use (uses get_llm() if None)
        max_complexity: Maximum complexity level (low, medium, high)
    """

    def __init__(self, model=None, max_complexity: str = "high"):
        self.model = model or get_llm()
        self.max_complexity = max_complexity

    def generate_spec(self, feature_request: str) -> SpecResult:
        """Generate structured spec from feature request in <5 min.

        Args:
            feature_request: Description of the feature to spec

        Returns:
            SpecResult with generated SpecDocument, timing, and suggestions
        """
        start = time.time()

        # Prompt LLM to decompose into user stories
        prompt = f"""Decompose this feature request into user stories with acceptance criteria.

Feature Request: {feature_request}

Return a JSON object with this structure:
{{
    "id": "spec-unique-id",
    "title": "Short descriptive title",
    "description": "Detailed description",
    "feature_request": "{feature_request}",
    "user_stories": [
        {{
            "id": "US-1",
            "description": "As a [role] I want [feature] so that [benefit]",
            "criteria": [
                {{
                    "id": "AC-1",
                    "description": "What must be true for this to be complete",
                    "verify_method": "How to verify (e.g., pytest tests/path.py)"
                }}
            ],
            "priority": "must"
        }}
    ],
    "technical_notes": "Any implementation notes",
    "estimated_complexity": "medium"
}}

Make sure to provide specific verification methods for each acceptance criterion.
"""

        # Call LLM and parse response
        from langchain_core.messages import HumanMessage

        response = self.model.invoke([HumanMessage(content=prompt)])
        spec_dict = parse_json_response(response.content)

        # Ensure id and created_at are set
        if "id" not in spec_dict or not spec_dict["id"]:
            spec_dict["id"] = "spec-" + str(int(time.time()))
        if "title" not in spec_dict:
            spec_dict["title"] = feature_request[:50]

        # Build SpecDocument
        spec = SpecDocument.from_dict(spec_dict)
        spec.created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ")

        generation_time = time.time() - start

        # Generate alternative suggestions
        suggestions = self._generate_suggestions(feature_request)

        return SpecResult(spec=spec, generation_time_seconds=generation_time, suggestions=suggestions)

    def _generate_suggestions(self, feature_request: str) -> list[str]:
        """Provide AI-powered alternative decompositions.

        Args:
            feature_request: The feature to generate alternatives for

        Returns:
            List of alternative decomposition suggestions
        """
        from langchain_core.messages import HumanMessage

        prompt = f"""Provide 2-3 alternative ways to decompose this feature request.
Focus on different angles: user journey, technical approach, or prioritization.

Feature: {feature_request}

Return suggestions as a JSON array or plain text list."""

        try:
            response = self.model.invoke([HumanMessage(content=prompt)])
            return parse_alternatives(response.content)
        except Exception:
            return []