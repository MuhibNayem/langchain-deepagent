"""Integration tests for tool execution lifecycle.

Tests to verify that tools complete execution without being cancelled.
"""
import tempfile
from pathlib import Path
import pytest
from langchain_core.messages import HumanMessage
from luminamind.deep_agent import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_file_write_completes():
    """Test that write_file tool completes without cancellation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test_write.txt"
        test_content = "Hello from integration test!"
        
        config = {"configurable": {"thread_id": "test-write-123"}}
        messages = [
            HumanMessage(
                content=f"Write the text '{test_content}' to the file {test_file}. "
                "Just do it directly, don't ask for confirmation."
            )
        ]
        
        # Stream the agent response
        final_state = None
        async for chunk in app.astream({"messages": messages}, config):
            final_state = chunk
        
        # Verify file was actually created (not cancelled)
        assert test_file.exists(), f"File should exist at {test_file}"
        content = test_file.read_text()
        assert test_content in content, f"File should contain expected content"


async def test_multiple_file_operations():
    """Test that multiple file operations complete without cancellation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file1 = Path(tmpdir) / "file1.txt"
        file2 = Path(tmpdir) / "file2.txt"
        file3 = Path(tmpdir) / "file3.txt"
        
        config = {"configurable": {"thread_id": "test-multi-123"}}
        messages = [
            HumanMessage(
                content=f"Create three files: {file1}, {file2}, and {file3}. "
                "Write 'Content 1', 'Content 2', and 'Content 3' respectively. "
                "Do it directly without asking for confirmation."
            )
        ]
        
        # Stream the agent response
        final_state = None
        async for chunk in app.astream({"messages": messages}, config):
            final_state = chunk
        
        # Verify all files were created
        assert file1.exists(), f"File 1 should exist"
        assert file2.exists(), f"File 2 should exist"
        assert file3.exists(), f"File 3 should exist"
        
        # Verify contents
        assert "Content 1" in file1.read_text()
        assert "Content 2" in file2.read_text()
        assert "Content 3" in file3.read_text()


async def test_file_delete_completes():
    """Test that file deletion completes without cancellation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "to_delete.txt"
        test_file.write_text("Delete me!")
        
        config = {"configurable": {"thread_id": "test-delete-123"}}
        messages = [
            HumanMessage(
                content=f"Delete the file {test_file}. Do it directly without asking."
            )
        ]
        
        # Stream the agent response
        final_state = None
        async for chunk in app.astream({"messages": messages}, config):
            final_state = chunk
        
        # Verify file was deleted
        assert not test_file.exists(), f"File should be deleted"


async def test_shell_command_completes():
    """Test that shell commands complete without cancellation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "shell_test.txt"
        
        config = {"configurable": {"thread_id": "test-shell-123"}}
        messages = [
            HumanMessage(
                content=f"Use the shell tool to run: echo 'Shell test' > {test_file}. "
                "Do it without asking for confirmation."
            )
        ]
        
        # Stream the agent response
        final_state = None
        async for chunk in app.astream({"messages": messages}, config):
            final_state = chunk
        
        # Verify file was created by shell command
        assert test_file.exists(), f"Shell command should have created file"
        assert "Shell test" in test_file.read_text()


async def test_no_tool_cancellation_errors():
    """Test that no 'tool was cancelled' errors occur during execution."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "cancel_test.txt"
        
        config = {"configurable": {"thread_id": "test-cancel-123"}}
        messages = [
            HumanMessage(
                content=f"Create a file at {test_file} with content 'Test'. "
                "Then rename it to {tmpdir}/renamed.txt. "
                "Do it without asking for confirmation."
            )
        ]
        
        # Stream and collect all messages
        all_messages = []
        async for chunk in app.astream({"messages": messages}, config):
            if "messages" in chunk.get("agent", {}):
                all_messages.extend(chunk["agent"]["messages"])
        
        # Check for cancellation errors in any message
        for msg in all_messages:
            content = str(getattr(msg, "content", ""))
            assert "cancelled" not in content.lower(), \
                f"Should not have cancellation errors. Found: {content}"
        
        # Verify operation succeeded
        renamed_file = Path(tmpdir) / "renamed.txt"
        assert renamed_file.exists(), "File should be renamed successfully"
