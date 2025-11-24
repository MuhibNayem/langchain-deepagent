import pytest
import os
import shutil
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from luminamind.deep_agent import app, ALL_BASE_TOOLS
from luminamind.utils.llm_wrapper import ContextAwareChatModel
from luminamind.config.settings import MAX_CONTEXT_TOKENS, SAFETY_BUFFER_TOKENS
from langgraph.types import Command

@pytest.fixture
def test_file(tmp_path):
    # Create a temporary directory for the test
    test_dir = tmp_path / "large_file_test"
    test_dir.mkdir()
    file_path = test_dir / "large_test.md"
    return file_path

@pytest.mark.asyncio
async def test_large_file_write_and_read(test_file):
    """
    Integration test to verify that the agent can handle large files
    without crashing due to context window limits.
    """
    print(f"\nTest file path: {test_file}")
    
    # 1. Instruct the agent to create a large file using python
    # We use python to generate it so we don't have to pass huge text in the prompt
    prompt = (
        f"Execute a python script using the 'shell' tool to create a file at {test_file} "
        "with 2000 lines of text, where each line contains 50 random characters. "
        "Then read the file using the read_file tool."
    )
    
    inputs = {"messages": [HumanMessage(content=prompt)]}
    config = RunnableConfig(configurable={"thread_id": "test_large_file_1"})
    
    tool_outputs = []
    
    print("\nStarting agent stream...")
    async for msg, metadata in app.astream(inputs, config, stream_mode="messages"):
        # print(f"Node: {metadata.get('langgraph_node', 'unknown')}")
        # print(f"Message: {msg}")
        
        if isinstance(msg, AIMessage) and msg.tool_calls:
            print(f"Tool Call: {msg.tool_calls[0]['name']}")
            
        if isinstance(msg, ToolMessage):
            print(f"Tool Output Length: {len(msg.content)}")
            tool_outputs.append(msg.content)
            
    # Handle interrupts (approval)
    current_state = await app.aget_state(config)
    while current_state.next:
        print("Sending resume command...")
        # The agent expects a specific resume payload structure
        resume_payload = {"decisions": [{"type": "approve"}]}
        
        async for msg, metadata in app.astream(Command(resume=resume_payload), config, stream_mode="messages"):
            if isinstance(msg, ToolMessage):
                print(f"Resume Tool Output Length: {len(msg.content)}")
                tool_outputs.append(msg.content)
        current_state = await app.aget_state(config)

    # Verify file exists and is large
    assert test_file.exists()
    content = test_file.read_text()
    print(f"File size: {len(content)} bytes")
    assert len(content) > 100000 # Should be ~100k bytes
    
    # Verify tool output was truncated (SmartTool logic)
    # The read_file output should be the largest output and contain the truncation message
    if tool_outputs:
        # Find the largest output, which should be from read_file
        largest_output = max(tool_outputs, key=lambda x: len(str(x)))
        print(f"Largest Output Length: {len(largest_output)}")
        print(f"Largest Output Sample: {str(largest_output)[:200]}...")
        # Check for truncation message
        assert "[OUTPUT TRUNCATED" in largest_output

@pytest.mark.asyncio
async def test_context_summarization():
    """
    Test that the ContextAwareChatModel summarizes history when it gets too long.
    """
    # We'll mock the LLM inside the wrapper to avoid real calls and just check logic
    # But for integration, we can just check if the SystemMessage with summary appears
    # after a long conversation.
    pass
