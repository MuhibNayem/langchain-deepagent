"""SpecBuilder for structured spec generation with feature decomposition.

Per PLAN-02: Structured output with feature decomposition into user stories
and acceptance criteria with specific verification methods.
"""
import hashlib
import time
from typing import Optional

from luminamind.planner.spec import SpecDocument, UserStory, AcceptanceCriterion


def parse_json_response(content: str) -> list:
    """Parse JSON from LLM response content.

    Handles markdown code blocks, plain JSON, and malformed JSON.
    Returns a list of dicts for user stories.
    """
    import json
    import re

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

    # Try to find JSON array in content
    json_str = json_str.strip()

    # Handle cases where LLM returns text before/after JSON
    if not json_str.startswith("["):
        # Try to find first [
        idx = json_str.find("[")
        if idx >= 0:
            json_str = json_str[idx:]
        # Try to find last ]
        idx = json_str.rfind("]")
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
            return []


class SpecBuilder:
    """Builds structured specifications from feature requests.

    Provides deterministic, structured spec generation with feature
    decomposition into user stories and acceptance criteria.

    Attributes:
        llm: Optional LLM for intelligent decomposition. If None, uses rule-based fallback.
    """

    def __init__(self, llm=None):
        """Initialize SpecBuilder.

        Args:
            llm: Optional LLM instance for intelligent decomposition.
                 If None, uses rule-based fallback.
        """
        self.llm = llm

    def decompose(self, feature_request: str) -> list[UserStory]:
        """Decompose feature request into user stories.

        Uses LLM if available, otherwise falls back to rule-based decomposition.

        Args:
            feature_request: Description of the feature to decompose

        Returns:
            List of UserStory objects
        """
        if self.llm:
            return self._llm_decompose(feature_request)
        return self._rule_based_decompose(feature_request)

    def _llm_decompose(self, feature_request: str) -> list[UserStory]:
        """Use LLM for intelligent decomposition.

        Args:
            feature_request: Description of the feature to decompose

        Returns:
            List of UserStory objects
        """
        from langchain_core.messages import HumanMessage

        prompt = f"""Decompose into user stories (As a [role] I want [feature] so that [benefit]):

Feature Request: {feature_request}

Return a JSON array with this structure:
[
    {{
        "id": "US-1",
        "description": "As a [role] I want [feature] so that [benefit]",
        "criteria": [
            {{
                "id": "AC-1",
                "description": "What must be true for completion",
                "verify_method": "How to verify (e.g., pytest tests/test_file.py::test_name)"
            }}
        ]
    }}
]

Make sure each user story has specific verification methods for acceptance criteria."""

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            data = parse_json_response(response.content)
            return [UserStory.from_dict(item) for item in data]
        except Exception:
            # Fallback on any error
            return self._rule_based_decompose(feature_request)

    def _rule_based_decompose(self, feature_request: str) -> list[UserStory]:
        """Rule-based fallback when LLM unavailable.

        Uses keyword extraction for basic decomposition.

        Args:
            feature_request: Description of the feature to decompose

        Returns:
            List of UserStory objects
        """
        words = feature_request.split()
        roles = self._extract_roles(words)
        features = self._extract_features(feature_request)

        user_stories = []
        # Pair roles with features
        for i, (role, feature) in enumerate(zip(roles, features), 1):
            story_id = f"US-{i}"
            desc = f"As a {role}, I want {feature} so that I can complete my task"
            criterion = AcceptanceCriterion(
                id=f"AC-{i}-1",
                description=f"Verify {feature} works correctly",
                verify_method=f"pytest tests/test_{feature.lower().replace(' ', '_')}.py"
            )
            user_stories.append(UserStory(
                id=story_id,
                description=desc,
                criteria=[criterion]
            ))

        # If no stories generated, create a generic one
        if not user_stories:
            user_stories.append(UserStory(
                id="US-1",
                description=f"As a user, I want {feature_request} so that I can complete my task",
                criteria=[
                    AcceptanceCriterion(
                        id="AC-1",
                        description=f"Verify {feature_request} works correctly",
                        verify_method="pytest tests/"
                    )
                ]
            ))

        return user_stories

    def _extract_roles(self, words: list[str]) -> list[str]:
        """Extract roles from feature request words.

        Args:
            words: List of words from feature request

        Returns:
            List of role names
        """
        role_keywords = ['user', 'admin', 'developer', 'system', 'customer', 'guest']
        roles = []
        for word in words:
            if word.lower() in role_keywords:
                roles.append(word)
        return roles if roles else ['user']

    def _extract_features(self, text: str) -> list[str]:
        """Extract features from text.

        Args:
            text: Feature request text

        Returns:
            List of feature phrases
        """
        # Basic: treat remaining significant words as features
        stopwords = {'the', 'a', 'an', 'to', 'for', 'and', 'or', 'with', 'that', 'this', 'my', 'i'}
        words = [w for w in text.split() if w.lower() not in stopwords and len(w) > 2]

        # Group into 2-4 word phrases as features
        features = []
        for i in range(0, len(words), 3):
            chunk = words[i:i+3]
            if chunk:
                features.append(' '.join(chunk))

        return features if features else [text]

    def generate_criteria(self, user_story: UserStory) -> list[AcceptanceCriterion]:
        """Generate acceptance criteria for a user story.

        Args:
            user_story: The user story to generate criteria for

        Returns:
            List of AcceptanceCriterion objects
        """
        if self.llm:
            return self._llm_generate_criteria(user_story)
        return self._rule_based_criteria(user_story)

    def _llm_generate_criteria(self, user_story: UserStory) -> list[AcceptanceCriterion]:
        """Use LLM to generate acceptance criteria.

        Args:
            user_story: The user story to generate criteria for

        Returns:
            List of AcceptanceCriterion objects
        """
        from langchain_core.messages import HumanMessage

        prompt = f"""Generate acceptance criteria for this user story:

Story: {user_story.description}

For each criterion provide:
- id: unique identifier (e.g., "AC-1")
- description: specific behavior to verify
- verify_method: specific test command or file (e.g., "pytest tests/test_login.py::test_login_success")
- priority: must, should, or could

Return a JSON array of criteria."""

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            data = parse_json_response(response.content)
            return [AcceptanceCriterion.from_dict(item) for item in data]
        except Exception:
            return self._rule_based_criteria(user_story)

    def _rule_based_criteria(self, user_story: UserStory) -> list[AcceptanceCriterion]:
        """Rule-based criteria generation when LLM unavailable.

        Args:
            user_story: The user story to generate criteria for

        Returns:
            List of AcceptanceCriterion objects
        """
        return [
            AcceptanceCriterion(
                id=f"{user_story.id}-AC1",
                description=f"Verify that {user_story.description.split('I want')[1].split('so that')[0].strip()} works as expected",
                verify_method="pytest tests/",
                priority="must"
            )
        ]

    def build_spec(self, feature_request: str, title: str = "") -> SpecDocument:
        """Build complete SpecDocument from feature request.

        Args:
            feature_request: Description of the feature to spec
            title: Optional title for the spec (uses first 50 chars of request if empty)

        Returns:
            SpecDocument with decomposed user stories and acceptance criteria
        """
        user_stories = self.decompose(feature_request)
        spec_id = hashlib.md5(feature_request.encode()).hexdigest()[:8]

        return SpecDocument(
            id=f"spec-{spec_id}",
            title=title or feature_request[:50],
            description=feature_request,
            feature_request=feature_request,
            user_stories=user_stories,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ")
        )