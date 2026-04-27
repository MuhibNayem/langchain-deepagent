import json

import pytest

from luminamind import main
from luminamind.py_tools.shell import shell


def test_stream_modes_validation_rejects_unknown_mode():
    assert main._parse_stream_modes("messages,updates") == ["messages", "updates"]
    with pytest.raises(Exception):
        main._parse_stream_modes("messages,unknown")


def test_file_backed_cli_transcript_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("LUMINAMIND_SESSION_ROOT", str(tmp_path))

    main._append_session_message("thread-a", "user", "hello")
    main._append_session_message("thread-a", "agent", "world")

    transcript = main._load_transcript("thread-a")
    assert [item["role"] for item in transcript] == ["user", "agent"]
    assert [item["content"] for item in transcript] == ["hello", "world"]

    export_path = tmp_path / "session.md"
    main._write_transcript_markdown("thread-a", transcript, export_path)
    exported = export_path.read_text(encoding="utf-8")
    assert "# LuminaMind Session thread-a" in exported
    assert "## user" in exported
    assert "world" in exported


def test_permission_profile_updates_shell_allowlist(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "PERMISSION_CONFIG", tmp_path / "permissions.json")

    try:
        main._set_permission_profile("locked")

        assert main._current_permission_profile() == "locked"
        assert main.os.environ["LUMINAMIND_REQUIRE_TOOL_APPROVAL"] == "1"
        assert shell.invoke({"command": "pwd"}).get("error") is False
        denied = shell.invoke({"command": "git status"})
        assert denied["error"] is True
        assert denied["allowed_commands"] == ["ls", "pwd", "which"]
    finally:
        main.os.environ.pop("LUMINAMIND_ALLOWED_SHELL_COMMANDS", None)
        main.os.environ.pop("LUMINAMIND_REQUIRE_TOOL_APPROVAL", None)


def test_detect_mcp_configs_reads_common_project_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".mcp.json").write_text(
        json.dumps({"mcpServers": {"playwright": {"command": "npx"}}}),
        encoding="utf-8",
    )

    configs = main._detect_mcp_configs()

    assert configs == [{"path": str(tmp_path / ".mcp.json"), "servers": ["playwright"]}]
