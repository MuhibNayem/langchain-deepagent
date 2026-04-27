from enum import Enum
from dataclasses import dataclass
from typing import Any


class AgentRole(Enum):
    PLANNER = "planner"
    GENERATOR = "generator"
    REVIEWER = "reviewer"
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"


@dataclass
class RoleSpecialization:
    role: AgentRole
    capabilities: list[str]
    max_instances: int = 3


class RoleRegistry:
    """Registry of agent roles and their specializations."""

    def __init__(self):
        self._roles: dict[AgentRole, RoleSpecialization] = {
            AgentRole.PLANNER: RoleSpecialization(
                role=AgentRole.PLANNER,
                capabilities=["planning", "decomposition", "spec_generation"],
            ),
            AgentRole.GENERATOR: RoleSpecialization(
                role=AgentRole.GENERATOR,
                capabilities=["code_generation", "file_writing", "refactoring"],
            ),
            AgentRole.REVIEWER: RoleSpecialization(
                role=AgentRole.REVIEWER,
                capabilities=["review", "critique", "grading"],
            ),
            AgentRole.COORDINATOR: RoleSpecialization(
                role=AgentRole.COORDINATOR,
                capabilities=["coordination", "task_routing", "load_balancing"],
            ),
            AgentRole.SPECIALIST: RoleSpecialization(
                role=AgentRole.SPECIALIST,
                capabilities=["domain_expertise"],
                max_instances=5,
            ),
        }

    def get(self, role: AgentRole) -> RoleSpecialization:
        return self._roles.get(role)

    def register(self, spec: RoleSpecialization):
        self._roles[spec.role] = spec