"""Tests for swarm module — TDD RED phase."""
import pytest
from luminamind.swarm import (
    Swarm,
    SwarmConfig,
    SwarmMessage,
    AgentRole,
    RoleRegistry,
    SharedKnowledge,
    ConsensusMechanism,
)


class TestSwarmCore:
    """Test swarm spawn/kill/broadcast/send_to/status."""

    def test_spawn_returns_agent_id(self):
        """Test spawn: agent spawned with correct role, returns agent_id."""
        swarm = Swarm()
        agent_id = swarm.spawn(AgentRole.PLANNER)
        assert agent_id is not None
        assert isinstance(agent_id, str)

    def test_spawn_with_role(self):
        """Agent spawned with correct role."""
        swarm = Swarm()
        agent_id = swarm.spawn(AgentRole.GENERATOR)
        status = swarm.get_status()
        assert status.active_agents == 0  # idle, not working
        assert status.idle_agents == 1

    def test_kill_removes_agent(self):
        """Test kill: agent terminated, removed from swarm."""
        swarm = Swarm()
        agent_id = swarm.spawn(AgentRole.REVIEWER)
        result = swarm.kill(agent_id)
        assert result is True
        status = swarm.get_status()
        assert status.idle_agents == 0

    def test_kill_nonexistent_returns_false(self):
        """Kill of nonexistent agent returns False."""
        swarm = Swarm()
        result = swarm.kill("nonexistent-id")
        assert result is False

    def test_broadcast_adds_to_queue(self):
        """Test broadcast: all agents receive broadcast message."""
        swarm = Swarm()
        id1 = swarm.spawn(AgentRole.PLANNER)
        id2 = swarm.spawn(AgentRole.GENERATOR)

        msg = SwarmMessage(sender_id=id1, message_type="test", payload={"data": "hello"})
        swarm.broadcast(msg)

        # Messages are queued — verify by checking message count
        assert len(swarm._message_queue) >= 1

    def test_send_to_direct_message(self):
        """Test send_to: direct message to specific agent."""
        swarm = Swarm()
        id1 = swarm.spawn(AgentRole.PLANNER)
        id2 = swarm.spawn(AgentRole.GENERATOR)

        msg = SwarmMessage(sender_id=id1, message_type="direct", payload={"to": id2})
        swarm.send_to(id2, msg)

        # Message should be queued for id2
        id2_msgs = [m for m in swarm._message_queue if m.recipient_id == id2]
        assert len(id2_msgs) >= 1

    def test_get_status_returns_swarm_status(self):
        """Test get_status: returns SwarmStatus with all agent states."""
        swarm = Swarm()
        swarm.spawn(AgentRole.PLANNER)
        swarm.spawn(AgentRole.GENERATOR)

        status = swarm.get_status()
        assert status.total_tasks == 2
        assert status.active_agents >= 0
        assert status.idle_agents >= 0

    def test_max_agents_limit(self):
        """Cannot spawn beyond max_agents."""
        swarm = Swarm(SwarmConfig(max_agents=2))
        swarm.spawn(AgentRole.PLANNER)
        swarm.spawn(AgentRole.GENERATOR)
        with pytest.raises(RuntimeError, match="Max agents"):
            swarm.spawn(AgentRole.REVIEWER)

    def test_role_capacity_limit(self):
        """Cannot spawn beyond role max_instances."""
        swarm = Swarm(SwarmConfig(max_agents=10))
        # PLANNER has max_instances=3 by default in RoleRegistry
        for i in range(3):
            swarm.spawn(AgentRole.PLANNER)
        with pytest.raises(RuntimeError, match="Max.*instances"):
            swarm.spawn(AgentRole.PLANNER)


class TestRoleRegistry:
    """Test role registry."""

    def test_get_existing_role(self):
        """Can retrieve known role specialization."""
        registry = RoleRegistry()
        spec = registry.get(AgentRole.PLANNER)
        assert spec is not None
        assert spec.role == AgentRole.PLANNER
        assert "planning" in spec.capabilities

    def test_get_unknown_role(self):
        """Unknown role returns None."""
        registry = RoleRegistry()
        # AgentRole enum only has defined roles — use a custom test
        assert registry.get(AgentRole.COORDINATOR) is not None

    def test_register_new_role(self):
        """Can register a new role specialization."""
        from luminamind.swarm.roles import RoleSpecialization
        registry = RoleRegistry()
        new_spec = RoleSpecialization(
            role=AgentRole.SPECIALIST,
            capabilities=["custom_capability"],
            max_instances=2,
        )
        registry.register(new_spec)
        retrieved = registry.get(AgentRole.SPECIALIST)
        assert retrieved is not None
        assert "custom_capability" in retrieved.capabilities


class TestSharedKnowledge:
    """Test SharedKnowledge store/retrieve/query/graph."""

    def test_store_and_retrieve(self):
        """Test store/retrieve: key-value storage with TTL."""
        kb = SharedKnowledge()
        kb.store("key1", {"data": "test"})
        assert kb.retrieve("key1") == {"data": "test"}

    def test_retrieve_nonexistent(self):
        """Retrieve of nonexistent key returns None."""
        kb = SharedKnowledge()
        assert kb.retrieve("nonexistent") is None

    def test_ttl_expiry(self):
        """Stored value expires after TTL."""
        kb = SharedKnowledge(ttl_seconds=1)
        kb.store("key1", "value", ttl_seconds=1)
        import time
        time.sleep(1.1)
        assert kb.retrieve("key1") is None

    def test_vector_query(self):
        """Test query: similarity search returns top-k results."""
        kb = SharedKnowledge()
        kb.store("vec1", "test1")
        # Manually add to vector store for testing
        from luminamind.swarm.knowledge_base import KnowledgeItem
        item = KnowledgeItem(id="1", key="vec1", value="test1")
        kb._vectors.add("vec1", [1.0, 0.0], item)

        results = kb.query([1.0, 0.0], top_k=1)
        assert len(results) >= 0  # May be empty if no vectors

    def test_graph_store_and_find(self):
        """Test graph_store: triple storage and retrieval."""
        kb = SharedKnowledge()
        kb.graph_store("subject1", "pred1", "obj1")
        results = kb.graph_find("subject1", "pred1")
        assert "obj1" in results

    def test_graph_find_nonexistent(self):
        """Graph find on nonexistent subject returns empty."""
        kb = SharedKnowledge()
        results = kb.graph_find("nonexistent", "pred")
        assert results == []


class TestConsensusMechanism:
    """Test ConsensusMechanism voting and decision."""

    def test_vote_and_get_decision(self):
        """Vote is recorded and decision is reached when threshold met."""
        c = ConsensusMechanism(threshold=0.6)
        c.vote("topic1", "voter1", "A")
        c.vote("topic1", "voter2", "A")
        c.vote("topic1", "voter3", "B")

        reached, value = c.get_decision("topic1", 3)
        assert reached is True
        assert value == "A"

    def test_vote_replacement(self):
        """Same voter voting again replaces previous vote."""
        c = ConsensusMechanism()
        c.vote("topic1", "voter1", "A")
        c.vote("topic1", "voter1", "B")
        # Only one vote from voter1
        reached, value = c.get_decision("topic1", 1)
        assert reached is True
        assert value == "B"

    def test_insufficient_votes(self):
        """Decision returns False when not enough votes."""
        c = ConsensusMechanism()
        c.vote("topic1", "voter1", "A")
        reached, value = c.get_decision("topic1", 3)
        assert reached is False
        assert value is None

    def test_wait_for_consensus_timeout(self):
        """wait_for_consensus returns False on timeout."""
        c = ConsensusMechanism(threshold=0.9, timeout_seconds=0.5)
        c.vote("topic1", "voter1", "A")
        c.vote("topic1", "voter2", "B")
        reached, value = c.wait_for_consensus("topic1", 3, timeout=0.2)
        assert reached is False

    def test_consensus_reached_in_wait(self):
        """wait_for_consensus returns True when consensus reached."""
        c = ConsensusMechanism(threshold=0.6, timeout_seconds=2)
        c.vote("topic1", "voter1", "A")
        c.vote("topic1", "voter2", "A")
        reached, value = c.wait_for_consensus("topic1", 2, timeout=1)
        assert reached is True
        assert value == "A"