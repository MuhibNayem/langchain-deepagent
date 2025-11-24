"""LLM wrapper for dynamic context management via summarization."""

import logging
from typing import Any, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

from luminamind.config.settings import MAX_CONTEXT_TOKENS, SAFETY_BUFFER_TOKENS, MIN_MESSAGES_TO_KEEP_TAIL
from luminamind.utils.content_manager import count_tokens

logger = logging.getLogger(__name__)


class ContextAwareChatModel(BaseChatModel):
    """
    A wrapper around a ChatModel that ensures the context window is not exceeded.
    It summarizes the middle of the conversation history using the LLM itself.
    """
    model: BaseChatModel
    
    def __init__(self, model: BaseChatModel, **kwargs):
        super().__init__(model=model, **kwargs)

    @property
    def _llm_type(self) -> str:
        return "context-aware-chat-model"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate a response with context management."""
        managed_messages = self._manage_context(messages)
        response_message = self.model.invoke(managed_messages, stop=stop, **kwargs)
        return ChatResult(generations=[ChatGeneration(message=response_message)])

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Asynchronously generate a response with context management."""
        # Note: For async, we should ideally use async summarization, 
        # but for simplicity we'll use the sync _manage_context or make it async later.
        # Since _manage_context might invoke the LLM, we should make it async-aware or just block.
        # For now, let's assume sync management is acceptable or we'll use the sync invoke inside.
        
        # Ideally, we should have _amanage_context.
        managed_messages = await self._amanage_context(messages)
        response_message = await self.model.ainvoke(managed_messages, stop=stop, **kwargs)
        return ChatResult(generations=[ChatGeneration(message=response_message)])

    def _manage_context(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """Synchronous context management."""
        total_tokens = sum(count_tokens(m.content) for m in messages)
        limit = MAX_CONTEXT_TOKENS - SAFETY_BUFFER_TOKENS
        
        if total_tokens <= limit:
            return messages
            
        return self._summarize_messages(messages, limit)

    async def _amanage_context(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """Asynchronous context management."""
        total_tokens = sum(count_tokens(m.content) for m in messages)
        limit = MAX_CONTEXT_TOKENS - SAFETY_BUFFER_TOKENS
        
        if total_tokens <= limit:
            return messages
            
        return await self._asummarize_messages(messages, limit)

    def _summarize_messages(self, messages: List[BaseMessage], limit: int) -> List[BaseMessage]:
        """Summarize the middle of the conversation."""
        logger.warning("Context limit exceeded. Summarizing history.")
        
        # Strategy: Keep System + First User + Last N. Summarize the rest.
        system_messages = [m for m in messages if isinstance(m, SystemMessage)]
        
        first_human = None
        remaining_messages = []
        for m in messages:
            if m in system_messages:
                continue
            if first_human is None and isinstance(m, HumanMessage):
                first_human = m
                continue
            remaining_messages.append(m)
            
        # Identify tail (Last N)
        tail_count = MIN_MESSAGES_TO_KEEP_TAIL
        if len(remaining_messages) <= tail_count:
            # Can't summarize if we don't have enough messages. 
            # Fallback to simple truncation or just return (risk crash)
            return messages
            
        to_summarize = remaining_messages[:-tail_count]
        tail_messages = remaining_messages[-tail_count:]
        
        # Generate Summary
        summary_text = self._generate_summary(to_summarize)
        
        summary_message = SystemMessage(content=f"[SYSTEM: Previous conversation summary: {summary_text}]")
        
        return system_messages + ([first_human] if first_human else []) + [summary_message] + tail_messages

    async def _asummarize_messages(self, messages: List[BaseMessage], limit: int) -> List[BaseMessage]:
        """Async version of summarization."""
        logger.warning("Context limit exceeded. Summarizing history (Async).")
        
        system_messages = [m for m in messages if isinstance(m, SystemMessage)]
        
        first_human = None
        remaining_messages = []
        for m in messages:
            if m in system_messages:
                continue
            if first_human is None and isinstance(m, HumanMessage):
                first_human = m
                continue
            remaining_messages.append(m)
            
        tail_count = MIN_MESSAGES_TO_KEEP_TAIL
        if len(remaining_messages) <= tail_count:
            return messages
            
        to_summarize = remaining_messages[:-tail_count]
        tail_messages = remaining_messages[-tail_count:]
        
        summary_text = await self._agenerate_summary(to_summarize)
        
        summary_message = SystemMessage(content=f"[SYSTEM: Previous conversation summary: {summary_text}]")
        
        return system_messages + ([first_human] if first_human else []) + [summary_message] + tail_messages

    def _generate_summary(self, messages: List[BaseMessage]) -> str:
        """Invoke LLM to summarize messages."""
        # Convert messages to a string representation
        conversation_text = ""
        for m in messages:
            role = m.type.upper()
            conversation_text += f"{role}: {m.content}\n"
            
        prompt = (
            "Summarize the following conversation history concisely. "
            "Preserve key decisions, tool executions, and the current state of the task. "
            "Do not lose important details needed for future steps.\n\n"
            f"{conversation_text}"
        )
        
        # We use the underlying model directly. 
        # We must ensure this call doesn't recurse infinitely. 
        # Since we call self.model.invoke, and self.model is the base model (not this wrapper), it's safe.
        response = self.model.invoke([HumanMessage(content=prompt)])
        return response.content

    async def _agenerate_summary(self, messages: List[BaseMessage]) -> str:
        """Async invoke LLM to summarize messages."""
        conversation_text = ""
        for m in messages:
            role = m.type.upper()
            conversation_text += f"{role}: {m.content}\n"
            
        prompt = (
            "Summarize the following conversation history concisely. "
            "Preserve key decisions, tool executions, and the current state of the task. "
            "Do not lose important details needed for future steps.\n\n"
            f"{conversation_text}"
        )
        
        response = await self.model.ainvoke([HumanMessage(content=prompt)])
        return response.content

    def bind_tools(self, tools: Any, **kwargs: Any) -> Any:
        """Bind tools to the underlying model."""
        return self.model.bind_tools(tools, **kwargs)
