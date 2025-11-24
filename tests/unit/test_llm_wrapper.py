"""Unit tests for ContextAwareChatModel wrapper."""

import pytest
from unittest.mock import Mock, MagicMock
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from luminamind.utils.llm_wrapper import ContextAwareChatModel
from luminamind.config.settings import MAX_CONTEXT_TOKENS, SAFETY_BUFFER_TOKENS, TRUNCATION_MESSAGE

# Mock tiktoken to avoid external dependency in unit tests and for predictable counts
# We'll assume 1 char = 1 token for simplicity in tests, or mock the count_tokens function
import luminamind.utils.content_manager as content_manager

@pytest.fixture
def mock_count_tokens(monkeypatch):
    """Mock count_tokens to return length of content for simple math."""
    def _mock_count(text):
        return len(text) if text else 0
    # Patch where it is imported and used
    monkeypatch.setattr("luminamind.utils.llm_wrapper.count_tokens", _mock_count)
    return _mock_count

from langchain_core.language_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration

class MockChatModel(BaseChatModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="Mock response"))])
    
    @property
    def _llm_type(self):
        return "mock"

@pytest.fixture
def mock_llm():
    model = MockChatModel()
    # We want to spy on invoke/bind_tools, so let's wrap it or mock methods
    # But Pydantic models are hard to mock methods on directly if they are fields.
    # Instead, let's use the MockChatModel as the base, but we can attach a mock to it to track calls?
    # Or just check the result?
    # Actually, ContextAwareChatModel calls self.model.invoke().
    # If we use a real class, we can't easily assert_called_once unless we mock the invoke method.
    # But invoke is defined in Runnable.
    
    # Let's use MagicMock with spec, but Pydantic checks isinstance.
    # So let's make a class that inherits from BaseChatModel AND MagicMock? No, multiple inheritance issues.
    
    # Use object.__setattr__ to bypass Pydantic's __setattr__ which forbids setting non-fields
    mock_invoke = Mock(return_value=AIMessage(content="Mock response"))
    object.__setattr__(model, "invoke", mock_invoke)
    
    mock_bind_tools = Mock()
    object.__setattr__(model, "bind_tools", mock_bind_tools)
    
    return model

def test_no_pruning_when_under_limit(mock_llm, mock_count_tokens):
    """Test that messages are not pruned when total tokens are under the limit."""
    wrapper = ContextAwareChatModel(model=mock_llm)
    
    # Create messages that are well under the limit (limit is ~120k)
    messages = [
        SystemMessage(content="System prompt"),
        HumanMessage(content="User message"),
    ]
    
    wrapper.invoke(messages)
    
    # Verify LLM was called with original messages
    mock_llm.invoke.assert_called_once()
    call_args = mock_llm.invoke.call_args
    assert call_args[0][0] == messages

def test_pruning_exceeds_limit(mock_llm, mock_count_tokens):
    """Test that messages are pruned when they exceed the limit."""
    wrapper = ContextAwareChatModel(model=mock_llm)
    
    # Limit is 120,000 - 4,000 = 116,000
    # Let's create a scenario where we exceed this.
    # We'll use a very large message to force pruning logic to trigger on history.
    
    # NOTE: The current implementation prunes *history*, but if a single message is too huge, 
    # it might still be an issue, but the logic tries to keep System + First User + Last N.
    
    # Let's construct a history:
    # 1. System (keep)
    # 2. User 1 (keep)
    # 3. AI 1 (prune)
    # 4. User 2 (prune)
    # 5. User 3 (keep - last message)
    
    # To trigger pruning, the total must be > 116,000.
    # Let's make the "prunable" messages huge.
    
    huge_text = "a" * 60000 # 60k tokens
    
    messages = [
        SystemMessage(content="System"), # ~6
        HumanMessage(content="First User"), # ~10
        AIMessage(content=huge_text), # 60k
        HumanMessage(content=huge_text), # 60k
        HumanMessage(content="Last User"), # ~9
    ]
    # Total ~ 120,025 > 116,000
    
    wrapper.invoke(messages)
    
    # Verify LLM was called with pruned messages
    mock_llm.invoke.assert_called_once()
    called_messages = mock_llm.invoke.call_args[0][0]
    
    # Check that we have fewer messages than original OR less content
    # In this specific case, we replaced 1 huge message with 1 truncation message, so count is same (5).
    # But content should be much less.
    original_len = sum(len(m.content) for m in messages)
    new_len = sum(len(m.content) for m in called_messages)
    assert new_len < original_len
    
    # Check that System and First User are preserved
    assert called_messages[0].content == "System"
    assert called_messages[1].content == "First User"
    
    # Check that Last User is preserved (it's the input)
    assert called_messages[-1].content == "Last User"
    
    # Check that a truncation message was inserted
    has_truncation = any(isinstance(m, SystemMessage) and "truncated" in m.content.lower() for m in called_messages)
    assert has_truncation

def test_bind_tools_delegation(mock_llm):
    """Test that bind_tools delegates to the underlying LLM."""
    wrapper = ContextAwareChatModel(model=mock_llm)
    tools = [Mock()]
    
    wrapper.bind_tools(tools)
    
    mock_llm.bind_tools.assert_called_once_with(tools)

def test_pruning_logic_preserves_structure(mock_llm, mock_count_tokens):
    """Test that the pruning logic maintains the correct message structure."""
    wrapper = ContextAwareChatModel(model=mock_llm)
    
    # Create a long conversation
    messages = [SystemMessage(content="Sys")]
    messages.append(HumanMessage(content="First"))
    
    # Add 100 intermediate messages of 2000 tokens each -> 200k tokens
    for i in range(100):
        messages.append(AIMessage(content="x" * 2000))
        
    messages.append(HumanMessage(content="Last"))
    
    wrapper.invoke(messages)
    
    called_messages = mock_llm.invoke.call_args[0][0]
    
    print(f"DEBUG: Called messages: {[type(m) for m in called_messages]}")
    for i, m in enumerate(called_messages):
        print(f"{i}: {type(m)} - {m.content[:20]}")
    
    # Should keep Sys, First, and some from the end
    assert called_messages[0] == messages[0]
    assert called_messages[1] == messages[1]
    assert called_messages[-1] == messages[-1]
    
    # Verify we are under limit (mock limit is huge, but logic should reduce it)
    # The logic keeps adding from the end until limit is reached.
    # So we should have a contiguous block of messages at the end.
    
    # Check for truncation marker
    assert isinstance(called_messages[2], SystemMessage)
    assert "truncated" in called_messages[2].content.lower()
