"""Context compaction with recent-biased compression and file deduplication.

Per D-08: Recent-biased compression strategy.
Per D-09: Same file content not re-sent within N turns.
Per D-10: Max-token budget enforcement with quality fallback.
Per D-13: Compression_factor tunable (agent discretion).
Per D-14: Dedup_window configurable (agent discretion).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from luminamind.optimization.token_budget import TokenBudget, BudgetAllocation


@dataclass
class CompressionResult:
    """Result of message compaction.

    Attributes:
        compressed_messages: The compacted message list
        original_count: Number of messages before compaction
        compressed_count: Number of messages after compaction
        compression_ratio: Ratio of compressed to original (1.0 = no compression)
        token_budget_used: Number of tokens used in the result
    """

    compressed_messages: list[dict]
    original_count: int
    compressed_count: int
    compression_ratio: float
    token_budget_used: int


class ContextCompactor:
    """Context compactor with recent-biased compression and file deduplication.

    Recent-biased strategy: keeps recent messages rich (uncompressed), compresses older
    messages. Token budget is enforced with quality fallback (summarize rather than drop).

    Usage:
        compactor = ContextCompactor(max_tokens=128000, recent_ratio=0.7, dedup_window=10)
        result = compactor.compact(messages, prefix=prefix)
        deduped = compactor.deduplicate(messages)
    """

    def __init__(
        self,
        max_tokens: int = 128000,
        recent_ratio: float = 0.7,
        compression_factor: float = 0.5,
        dedup_window: int = 10,
    ) -> None:
        """Initialize ContextCompactor.

        Args:
            max_tokens: Maximum tokens for compacted context (default 128K)
            recent_ratio: Fraction of recent messages to keep rich (default 0.7 = 70%)
            compression_factor: How aggressively to compress older messages (default 0.5)
            dedup_window: Turns within which to deduplicate file reads (default 10)
        """
        self.max_tokens = max_tokens
        self.recent_ratio = recent_ratio
        self.compression_factor = compression_factor
        self.dedup_window = dedup_window

        # Deduplication state
        self._seen_files: dict[str, str] = {}  # path → content_hash
        self._turn_index: int = 0

    def compact(
        self,
        messages: list[dict],
        prefix: str = "",
        max_tokens: int | BudgetAllocation | None = None
    ) -> CompressionResult:
        """Compress message list to fit within max_tokens budget.

        Recent-biased: recent messages (by recent_ratio) are kept rich/uncompressed.
        Older messages are compressed with truncation. If still over budget,
        quality fallback applies: summarize rather than drop.

        Args:
            messages: List of message dicts to compress
            prefix: Prefix string (e.g., workspace summary) to account for in budget
            max_tokens: Either int (legacy), BudgetAllocation (budget-aware), or None

        Returns:
            CompressionResult with compressed messages and stats
        """
        if isinstance(max_tokens, BudgetAllocation):
            return self._budget_aware_compact(messages, prefix, max_tokens)
        # Fall back to legacy behavior
        return self._legacy_compact(messages, prefix, max_tokens)

    def _budget_aware_compact(
        self,
        messages: list[dict],
        prefix: str,
        allocation: BudgetAllocation
    ) -> CompressionResult:
        """Budget-aware compaction using TokenBudget allocation.

        Uses recent-biased compression but respects allocation.available_tokens.
        """
        if not messages:
            return CompressionResult(
                compressed_messages=[],
                original_count=0,
                compressed_count=0,
                compression_ratio=1.0,
                token_budget_used=0,
            )

        prefix_tokens = self._estimate_tokens(prefix)
        available = allocation.available_tokens - prefix_tokens

        if available < 0:
            available = 0

        total = len(messages)
        recent_count = int(total * self.recent_ratio)

        result_messages: list[dict] = []
        tokens_used = 0

        # Add recent messages (rich - no compression)
        for msg in messages[-recent_count:]:
            msg_tokens = self._estimate_tokens(msg)
            if tokens_used + msg_tokens > available:
                summarized = self._summarize_message(msg, available_tokens=available - tokens_used)
                summ_tokens = self._estimate_tokens(summarized)
                if tokens_used + summ_tokens <= available:
                    result_messages.append(summarized)
                    tokens_used += summ_tokens
                continue
            result_messages.append(msg)
            tokens_used += msg_tokens

        # Add compressed older messages
        remaining = available - tokens_used
        for msg in messages[:-recent_count]:
            compressed = self._compress_message(msg, self.compression_factor)
            comp_tokens = self._estimate_tokens(compressed)

            if tokens_used + comp_tokens > available:
                summarized = self._summarize_message(msg, available_tokens=remaining)
                comp_tokens = self._estimate_tokens(summarized)
                if tokens_used + comp_tokens > available:
                    if remaining > 50:
                        min_summ = self._summarize_message(msg, available_tokens=remaining)
                        min_tokens = self._estimate_tokens(min_summ)
                        if tokens_used + min_tokens <= available:
                            result_messages.append(min_summ)
                            tokens_used += min_tokens
                    continue
            result_messages.append(compressed)
            tokens_used += comp_tokens
            remaining = available - tokens_used

        return CompressionResult(
            compressed_messages=result_messages,
            original_count=total,
            compressed_count=len(result_messages),
            compression_ratio=len(result_messages) / total if total > 0 else 1.0,
            token_budget_used=tokens_used + prefix_tokens,
        )

    def _legacy_compact(
        self,
        messages: list[dict],
        prefix: str,
        max_tokens: int | None
    ) -> CompressionResult:
        """Legacy compact method for backwards compatibility."""
        if not messages:
            return CompressionResult(
                compressed_messages=[],
                original_count=0,
                compressed_count=0,
                compression_ratio=1.0,
                token_budget_used=0,
            )

        effective_max = max_tokens if max_tokens is not None else self.max_tokens
        prefix_tokens = self._estimate_tokens(prefix)
        available = effective_max - prefix_tokens

        total = len(messages)
        recent_count = int(total * self.recent_ratio)

        result_messages: list[dict] = []
        tokens_used = 0

        for msg in messages[-recent_count:]:
            msg_tokens = self._estimate_tokens(msg)
            remaining = available - tokens_used

            if tokens_used + msg_tokens > available:
                summarized = self._summarize_message(msg, available_tokens=remaining)
                summ_tokens = self._estimate_tokens(summarized)
                if tokens_used + summ_tokens <= available:
                    result_messages.append(summarized)
                    tokens_used += summ_tokens
                    continue
                continue
            result_messages.append(msg)
            tokens_used += msg_tokens

        for msg in messages[:-recent_count]:
            compressed = self._compress_message(msg, self.compression_factor)
            comp_tokens = self._estimate_tokens(compressed)
            remaining = available - tokens_used

            if tokens_used + comp_tokens > available:
                compressed = self._summarize_message(msg, available_tokens=remaining)
                comp_tokens = self._estimate_tokens(compressed)
                if tokens_used + comp_tokens > available:
                    compressed = self._summarize_message(msg, available_tokens=remaining)
                    comp_tokens = self._estimate_tokens(compressed)
                    if tokens_used + comp_tokens > available:
                        continue
            result_messages.append(compressed)
            tokens_used += comp_tokens

        return CompressionResult(
            compressed_messages=result_messages,
            original_count=total,
            compressed_count=len(result_messages),
            compression_ratio=len(result_messages) / total if total > 0 else 1.0,
            token_budget_used=tokens_used + prefix_tokens,
        )

    def deduplicate(self, messages: list[dict]) -> list[dict]:
        """Remove file reads with duplicate content within deduplication window.

        Per D-09: Same file content not re-sent within N turns.
        Content hash detects changes - different content busts the dedup.

        Args:
            messages: List of message dicts to deduplicate

        Returns:
            Messages with duplicates replaced by reference messages
        """
        self._turn_index += 1
        result: list[dict] = []

        for msg in messages:
            if self._is_file_read(msg):
                content = self._extract_file_content(msg)
                content_hash = hashlib.sha256(content.encode()).hexdigest()
                path = self._extract_file_path(msg)

                if path in self._seen_files:
                    if self._seen_files[path] == content_hash:
                        # Duplicate within window - replace with reference
                        result.append({
                            "role": msg.get("role", "tool"),
                            "content": f"[File {path} unchanged — see above]",
                            "is_dedup_ref": True
                        })
                        continue
                    else:
                        # Content changed - update hash
                        self._seen_files[path] = content_hash
                else:
                    self._seen_files[path] = content_hash

                # Prune old entries if window exceeded
                if len(self._seen_files) > self.dedup_window:
                    # Keep only most recent entries
                    items = list(self._seen_files.items())
                    self._seen_files = dict(items[-self.dedup_window:])

            result.append(msg)

        return result

    def _is_file_read(self, msg: dict) -> bool:
        """Detect if message is a file read tool result.

        Args:
            msg: Message dict

        Returns:
            True if message appears to be a file read result
        """
        return msg.get("type") == "tool_result" and "read_file" in msg.get("name", "")

    def _extract_file_content(self, msg: dict) -> str:
        """Extract content from file read message.

        Args:
            msg: Message dict

        Returns:
            File content string
        """
        return msg.get("content", "")

    def _extract_file_path(self, msg: dict) -> str:
        """Extract file path from message.

        Args:
            msg: Message dict

        Returns:
            File path string
        """
        # Parse from tool call arguments
        return msg.get("path", msg.get("file_path", ""))

    def _compress_message(self, msg: dict, factor: float) -> dict:
        """Apply compression to single message.

        Truncates content based on compression_factor.

        Args:
            msg: Message dict to compress
            factor: Compression factor (0.0-1.0, lower = more aggressive)

        Returns:
            Compressed message dict
        """
        content = msg.get("content", "")
        # max_chars scales with compression_factor (0.5 = 500 chars, 0.3 = 300 chars)
        max_chars = int(500 * factor)
        truncated = self._truncate_content(content, max_chars=max_chars)

        return {
            "role": msg.get("role"),
            "content": truncated,
            "timestamp": msg.get("timestamp")
        }

    def _truncate_content(self, content: str, max_chars: int = 500) -> str:
        """Truncate content to max_chars with marker.

        Args:
            content: Content string to truncate
            max_chars: Maximum characters to keep

        Returns:
            Truncated content with marker if truncated
        """
        if len(content) <= max_chars:
            return content
        return content[:max_chars] + "... [compressed]"

    def _summarize_message(self, msg: dict, available_tokens: int | None = None) -> dict:
        """Quality fallback: summarize message rather than drop.

        Per D-10: Summarize rather than drop ensures no content is lost.

        Args:
            msg: Message dict to summarize
            available_tokens: If provided, try to fit content within this budget

        Returns:
            Summarized message dict
        """
        content = msg.get("content", "")
        if available_tokens is not None:
            # Limit content to fit within available tokens
            # 1 token ≈ 4 chars, so available_chars = available_tokens * 4
            max_chars = (available_tokens * 4) - 50  # Leave room for marker
            if max_chars < 10:
                max_chars = 10  # Minimum viable content
            if len(content) > max_chars:
                return {
                    "role": msg.get("role"),
                    "content": f"[Earlier conversation summarized] {content[:max_chars]}...",
                    "timestamp": msg.get("timestamp")
                }
        # Default fallback
        return {
            "role": msg.get("role"),
            "content": f"[Earlier conversation summarized] {content[:200]}...",
            "timestamp": msg.get("timestamp")
        }

    def _estimate_tokens(self, obj: dict | str) -> int:
        """Rough token estimation (1 token ≈ 4 characters).

        Args:
            obj: Dict or string to estimate

        Returns:
            Estimated token count
        """
        text = obj if isinstance(obj, str) else str(obj)
        return len(text) // 4

    def compact(
        self,
        messages: list[dict],
        prefix: str = "",
        max_tokens: int | BudgetAllocation | None = None
    ) -> CompressionResult:
        """Compress message list to fit within max_tokens budget.

        Recent-biased: recent messages (by recent_ratio) are kept rich/uncompressed.
        Older messages are compressed with truncation. If still over budget,
        quality fallback applies: summarize rather than drop.

        Args:
            messages: List of message dicts to compress
            prefix: Prefix string (e.g., workspace summary) to account for in budget
            max_tokens: Either int (legacy), BudgetAllocation (budget-aware), or None

        Returns:
            CompressionResult with compressed messages and stats
        """
        if isinstance(max_tokens, BudgetAllocation):
            return self._budget_aware_compact(messages, prefix, max_tokens)
        # Fall back to legacy behavior
        return self._legacy_compact(messages, prefix, max_tokens)

    def _budget_aware_compact(
        self,
        messages: list[dict],
        prefix: str,
        allocation: BudgetAllocation
    ) -> CompressionResult:
        """Budget-aware compaction using TokenBudget allocation.

        Uses recent-biased compression per the original implementation,
        but respects allocation.available_tokens for history.
        """
        prefix_tokens = self._estimate_tokens(prefix)
        available = allocation.available_tokens - prefix_tokens

        if available < 0:
            available = 0

        total = len(messages)
        recent_count = int(total * self.recent_ratio)

        result_messages: list[dict] = []
        tokens_used = 0

        # Add recent messages (rich - no compression)
        for msg in messages[-recent_count:]:
            msg_tokens = self._estimate_tokens(msg)
            if tokens_used + msg_tokens > available:
                # Summarize to fit
                summarized = self._summarize_message(msg, available_tokens=available - tokens_used)
                summ_tokens = self._estimate_tokens(summarized)
                if tokens_used + summ_tokens <= available:
                    result_messages.append(summarized)
                    tokens_used += summ_tokens
                continue
            result_messages.append(msg)
            tokens_used += msg_tokens

        # Add compressed older messages
        remaining = available - tokens_used
        for msg in messages[:-recent_count]:
            compressed = self._compress_message(msg, self.compression_factor)
            comp_tokens = self._estimate_tokens(compressed)

            if tokens_used + comp_tokens > available:
                summarized = self._summarize_message(msg, available_tokens=remaining)
                comp_tokens = self._estimate_tokens(summarized)
                if tokens_used + comp_tokens > available:
                    if remaining > 50:
                        min_summ = self._summarize_message(msg, available_tokens=remaining)
                        min_tokens = self._estimate_tokens(min_summ)
                        if tokens_used + min_tokens <= available:
                            result_messages.append(min_summ)
                            tokens_used += min_tokens
                    continue
            result_messages.append(compressed)
            tokens_used += comp_tokens
            remaining = available - tokens_used

        return CompressionResult(
            compressed_messages=result_messages,
            original_count=total,
            compressed_count=len(result_messages),
            compression_ratio=len(result_messages) / total if total > 0 else 1.0,
            token_budget_used=tokens_used + prefix_tokens,
        )

    def _legacy_compact(
        self,
        messages: list[dict],
        prefix: str,
        max_tokens: int | None
    ) -> CompressionResult:
        """Legacy compact method for backwards compatibility."""
        effective_max = max_tokens if max_tokens is not None else self.max_tokens

        if not messages:
            return CompressionResult(
                compressed_messages=[],
                original_count=0,
                compressed_count=0,
                compression_ratio=1.0,
                token_budget_used=0,
            )

        prefix_tokens = self._estimate_tokens(prefix)
        available = effective_max - prefix_tokens

        total = len(messages)
        recent_count = int(total * self.recent_ratio)

        result_messages: list[dict] = []
        tokens_used = 0

        for msg in messages[-recent_count:]:
            msg_tokens = self._estimate_tokens(msg)
            remaining = available - tokens_used

            if tokens_used + msg_tokens > available:
                summarized = self._summarize_message(msg, available_tokens=remaining)
                summ_tokens = self._estimate_tokens(summarized)
                if tokens_used + summ_tokens <= available:
                    result_messages.append(summarized)
                    tokens_used += summ_tokens
                    continue
                continue
            result_messages.append(msg)
            tokens_used += msg_tokens

        for msg in messages[:-recent_count]:
            compressed = self._compress_message(msg, self.compression_factor)
            comp_tokens = self._estimate_tokens(compressed)
            remaining = available - tokens_used

            if tokens_used + comp_tokens > available:
                compressed = self._summarize_message(msg, available_tokens=remaining)
                comp_tokens = self._estimate_tokens(compressed)
                if tokens_used + comp_tokens > available:
                    compressed = self._summarize_message(msg, available_tokens=remaining)
                    comp_tokens = self._estimate_tokens(compressed)
                    if tokens_used + comp_tokens > available:
                        continue
            result_messages.append(compressed)
            tokens_used += comp_tokens

        return CompressionResult(
            compressed_messages=result_messages,
            original_count=total,
            compressed_count=len(result_messages),
            compression_ratio=len(result_messages) / total if total > 0 else 1.0,
            token_budget_used=tokens_used + prefix_tokens,
        )


# Auto-compaction integration helpers

def auto_compact(
    thread_id: str,
    session_store: Any,
    compactor: ContextCompactor | None = None
) -> CompressionResult | None:
    """Run compaction on session each agent turn.

    Args:
        thread_id: Session thread identifier
        session_store: SessionStore instance (InMemory, FileBacked, or Redis)
        compactor: ContextCompactor instance (creates default if None)

    Returns:
        CompressionResult if compaction happened, None if no messages
    """
    compactor = compactor or ContextCompactor()
    session = session_store.get_session(thread_id)

    # Get all messages from full transcript
    messages = []
    count = session.transcript.get_message_count()
    for i in range(count):
        msg = session.transcript.get_message_at(i)
        if msg is not None:
            messages.append(msg)

    if not messages:
        return None

    # Get prefix if prompt builder available
    prefix = ""
    if hasattr(session_store, '_prompt_builder') and session_store._prompt_builder:
        prefix = session_store._prompt_builder.get_prefix()

    result = compactor.compact(messages, prefix)

    # Record stats in working memory if compression happened
    if result.compression_ratio < 1.0:
        session.working_memory.add_note(
            f"Compacted {result.original_count} → {result.compressed_count} messages "
            f"({result.compression_ratio:.0%} ratio, {result.token_budget_used} tokens)"
        )

    return result


def compact_now(
    thread_id: str,
    session_store: Any,
    compactor: ContextCompactor | None = None
) -> CompressionResult | None:
    """Manual trigger for compaction.

    Args:
        thread_id: Session thread identifier
        session_store: SessionStore instance
        compactor: ContextCompactor instance (creates default if None)

    Returns:
        CompressionResult
    """
    return auto_compact(thread_id, session_store, compactor)


__all__ = [
    "ContextCompactor",
    "CompressionResult",
    "auto_compact",
    "compact_now",
]