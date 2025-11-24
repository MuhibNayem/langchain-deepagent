import os

# Context Window Settings
# 128k is the limit for GLM-4-Flash and many modern models.
# We set a safe limit to trigger management before we hit the hard wall.
MAX_CONTEXT_TOKENS = 120000
SAFETY_BUFFER_TOKENS = 4000
MAX_TOOL_OUTPUT_TOKENS = 8000

# Summarization Settings
# When summarizing, we want to keep the system prompt and the most recent messages.
# We will summarize the "middle" of the conversation.
MIN_MESSAGES_TO_KEEP_TAIL = 10  # Keep at least the last 10 messages raw
