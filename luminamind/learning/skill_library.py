"""Skill Library with Versioning, Search, and Persistence.

Manages the persistent skill catalog with version control,
full-text search, and rollback capability.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, TYPE_CHECKING
import json

from luminamind.learning.skill_acquirer import AtomicSkill

if TYPE_CHECKING:
    from luminamind.learning.feedback_loop import FeedbackSignal


class SkillLibrary:
    """Persistent skill library with versioning, search, and suggestion.

    Stores skills in ~/.luminamind/skills/{skill_id}/v{version}.json
    Maintains SKILLS.md as a human-readable catalog index.
    """

    def __init__(self, base_path: Path = Path("~/.luminamind/skills")):
        """Initialize SkillLibrary.

        Args:
            base_path: Base directory for skill storage (default: ~/.luminamind/skills)
        """
        self.base_path = Path(base_path).expanduser()
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, dict] = {}  # skill_id -> skill metadata

    def register(self, skill: AtomicSkill) -> str:
        """Register a new skill. Returns skill_id.

        Saves skill to ~/.luminamind/skills/{skill_id}/v{version}.json
        Updates SKILLS.md index

        Args:
            skill: AtomicSkill to register

        Returns:
            The skill_id of the registered skill
        """
        skill_dir = self.base_path / skill.id
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Save skill data
        skill_path = skill_dir / f"v{skill.version}.json"
        skill_data = self._skill_to_dict(skill)
        with open(skill_path, "w") as f:
            json.dump(skill_data, f, indent=2, default=str)

        # Update index
        self._index[skill.id] = {
            "id": skill.id,
            "name": skill.name,
            "version": skill.version,
            "path": str(skill_path),
        }

        # Update SKILLS.md catalog
        self._update_catalog()

        return skill.id

    def improve(self, skill_id: str, feedback: "FeedbackSignal") -> None:
        """Update skill based on feedback. Creates new version.

        Args:
            skill_id: ID of skill to improve
            feedback: Feedback signal with improvement data
        """
        # Get current skill
        skill = self.get(skill_id)
        if skill is None:
            return

        # Create new version
        skill.version += 1
        skill.success_rate = self._calculate_new_success_rate(skill, feedback)
        skill.last_used = __import__("datetime").datetime.now()

        # Save new version
        self.register(skill)

    def search(self, query: str, limit: int = 10) -> list[AtomicSkill]:
        """Full-text search over skill names, descriptions, trigger conditions.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of matching AtomicSkill instances
        """
        results = []
        query_lower = query.lower()

        for skill_id in self._index:
            skill = self.get(skill_id)
            if skill is None:
                continue

            # Score based on match
            score = 0
            if query_lower in skill.name.lower():
                score += 3
            if query_lower in skill.description.lower():
                score += 2
            for trigger in skill.trigger_conditions:
                if query_lower in trigger.lower():
                    score += 1

            if score > 0:
                results.append((skill, score))

        # Sort by score and return top results
        results.sort(key=lambda x: x[1], reverse=True)
        return [skill for skill, _ in results[:limit]]

    def get(self, skill_id: str, version: int | None = None) -> AtomicSkill | None:
        """Get skill by ID, optionally at specific version.

        Args:
            skill_id: ID of the skill to retrieve
            version: Specific version to retrieve (default: latest)

        Returns:
            AtomicSkill if found, None otherwise
        """
        if skill_id not in self._index:
            return None

        version_str = f"v{version}.json" if version else None
        skill_dir = self.base_path / skill_id

        if version_str:
            skill_path = skill_dir / version_str
        else:
            # Get latest version
            files = list(skill_dir.glob("v*.json"))
            if not files:
                return None
            files.sort(key=lambda f: f.name)
            skill_path = files[-1]

        if not skill_path.exists():
            return None

        with open(skill_path) as f:
            data = json.load(f)

        return self._dict_to_skill(data)

    def list_versions(self, skill_id: str) -> list[int]:
        """List all versions for a skill.

        Args:
            skill_id: ID of the skill

        Returns:
            List of version numbers (oldest first)
        """
        skill_dir = self.base_path / skill_id
        if not skill_dir.exists():
            return []

        versions = []
        for f in skill_dir.glob("v*.json"):
            try:
                v = int(f.stem[1:])  # Extract version from "v{n}.json"
                versions.append(v)
            except ValueError:
                continue

        return sorted(versions)

    def rollback(self, skill_id: str, target_version: int) -> bool:
        """Rollback skill to a previous version.

        Args:
            skill_id: ID of the skill to rollback
            target_version: Version number to rollback to

        Returns:
            True if rollback successful, False otherwise
        """
        # Verify target version exists
        versions = self.list_versions(skill_id)
        if target_version not in versions:
            return False

        # Get the target version skill
        skill = self.get(skill_id, version=target_version)
        if skill is None:
            return False

        # Create new version from the target (not a true rollback, just copying)
        skill.version = target_version + 1
        self.register(skill)

        return True

    def get_skill_catalog(self) -> str:
        """Generate SKILLS.md content for the skill catalog.

        Returns:
            Markdown string for the SKILLS.md catalog
        """
        lines = ["# Skill Catalog", "", "## Atomic Skills", ""]

        for skill_id in sorted(self._index.keys()):
            skill = self.get(skill_id)
            if skill is None:
                continue

            lines.append(f"### {skill.name}")
            lines.append(f"- **ID:** {skill.id}")
            lines.append(f"- **Version:** {skill.version}")
            lines.append(f"- **Description:** {skill.description}")
            lines.append(f"- **Trigger:** {', '.join(skill.trigger_conditions[:5])}")
            lines.append(f"- **Success Rate:** {skill.success_rate * 100:.1f}%")
            lines.append(f"- **Avg Tokens Saved:** {skill.avg_tokens_saved:.0f}")
            lines.append("")

        return "\n".join(lines)

    def _update_catalog(self) -> None:
        """Update the SKILLS.md catalog file."""
        catalog_path = self.base_path / "SKILLS.md"
        catalog_content = self.get_skill_catalog()
        with open(catalog_path, "w") as f:
            f.write(catalog_content)

    def _skill_to_dict(self, skill: AtomicSkill) -> dict:
        """Convert AtomicSkill to dict for JSON serialization."""
        return {
            "id": skill.id,
            "name": skill.name,
            "description": skill.description,
            "trigger_conditions": skill.trigger_conditions,
            "actions": skill.actions,
            "success_rate": skill.success_rate,
            "avg_tokens_saved": skill.avg_tokens_saved,
            "version": skill.version,
            "created_at": skill.created_at.isoformat() if isinstance(skill.created_at, datetime) else skill.created_at,
            "last_used": skill.last_used.isoformat() if isinstance(skill.last_used, datetime) else skill.last_used,
            "metadata": skill.metadata,
        }

    def _dict_to_skill(self, data: dict) -> AtomicSkill:
        """Convert dict back to AtomicSkill."""
        from datetime import datetime

        # Handle datetime fields
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        last_used = data.get("last_used")
        if isinstance(last_used, str):
            last_used = datetime.fromisoformat(last_used)

        return AtomicSkill(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            trigger_conditions=data.get("trigger_conditions", []),
            actions=data.get("actions", []),
            success_rate=data.get("success_rate", 0.0),
            avg_tokens_saved=data.get("avg_tokens_saved", 0.0),
            version=data.get("version", 1),
            created_at=created_at or datetime.now(),
            last_used=last_used or datetime.now(),
            metadata=data.get("metadata", {}),
        )

    def _calculate_new_success_rate(self, skill: AtomicSkill, feedback: "FeedbackSignal") -> float:
        """Calculate new success rate based on feedback."""
        # TODO: Implement weighted success rate calculation
        return skill.success_rate


# Stub for type hints
class FeedbackSignal:
    """Stub for FeedbackSignal from feedback_loop module."""
    pass
