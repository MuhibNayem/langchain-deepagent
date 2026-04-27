from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import uuid


@dataclass
class ExecutionBranch:
    """A branch in agent execution (subagent spawn, parallel task)."""
    branch_id: str
    parent_branch_id: str | None
    branch_name: str
    started_at: datetime
    completed_at: datetime | None = None
    status: str = "running"  # running, completed, failed
    result: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ExecutionTree:
    """Tree of all execution branches."""
    tree_id: str
    root_branch_id: str
    created_at: datetime
    branches: dict[str, ExecutionBranch] = field(default_factory=dict)

    def add_branch(self, branch: ExecutionBranch) -> None:
        """Add a branch."""
        self.branches[branch.branch_id] = branch

    def get_branch(self, branch_id: str) -> ExecutionBranch | None:
        """Get branch by ID."""
        return self.branches.get(branch_id)

    def get_children(self, branch_id: str) -> list[ExecutionBranch]:
        """Get child branches."""
        return [
            b for b in self.branches.values()
            if b.parent_branch_id == branch_id
        ]

    def get_root(self) -> ExecutionBranch:
        """Get root branch."""
        return self.branches[self.root_branch_id]

    def to_tree_format(self) -> dict:
        """Convert to tree visualization format."""
        def build_node(branch_id: str) -> dict:
            branch = self.branches[branch_id]
            return {
                'id': branch.branch_id,
                'name': branch.branch_name,
                'status': branch.status,
                'started_at': branch.started_at.isoformat(),
                'completed_at': branch.completed_at.isoformat() if branch.completed_at else None,
                'result': branch.result,
                'metadata': branch.metadata,
                'children': [build_node(child.branch_id) for child in self.get_children(branch_id)]
            }

        return {
            'tree_id': self.tree_id,
            'created_at': self.created_at.isoformat(),
            'root': build_node(self.root_branch_id)
        }


class BranchingVisualizer:
    """Visualizes branching in agent execution."""

    def __init__(self):
        self._active_trees: dict[str, ExecutionTree] = {}

    async def start_tree(self, agent_id: str, session_id: str,
                         task_id: str, root_name: str) -> ExecutionTree:
        """Start a new execution tree."""
        tree_id = str(uuid.uuid4())[:8]
        root = ExecutionBranch(
            branch_id=f"{tree_id}-root",
            parent_branch_id=None,
            branch_name=root_name,
            started_at=datetime.utcnow()
        )

        tree = ExecutionTree(
            tree_id=tree_id,
            root_branch_id=root.branch_id,
            branches={root.branch_id: root},
            created_at=datetime.utcnow()
        )

        self._active_trees[tree_id] = tree
        return tree

    async def spawn_branch(self, tree_id: str, parent_branch_id: str,
                          branch_name: str) -> ExecutionBranch:
        """Spawn a new branch."""
        tree = self._active_trees.get(tree_id)
        if not tree:
            raise ValueError(f"No active tree with ID: {tree_id}")

        branch = ExecutionBranch(
            branch_id=f"{tree_id}-branch-{len(tree.branches)}",
            parent_branch_id=parent_branch_id,
            branch_name=branch_name,
            started_at=datetime.utcnow()
        )
        tree.add_branch(branch)
        return branch

    async def complete_branch(self, tree_id: str, branch_id: str,
                             result: str | None = None, status: str = "completed") -> None:
        """Mark branch as completed."""
        tree = self._active_trees.get(tree_id)
        if not tree:
            raise ValueError(f"No active tree with ID: {tree_id}")

        branch = tree.get_branch(branch_id)
        if branch:
            branch.completed_at = datetime.utcnow()
            branch.status = status
            branch.result = result

    async def end_tree(self, tree_id: str) -> ExecutionTree:
        """End tree and return it."""
        return self._active_trees.pop(tree_id)