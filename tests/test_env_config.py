"""Tests for project-local environment loading."""

from __future__ import annotations

from pathlib import Path

from src import env_config


def test_parse_env_line():
    assert env_config._parse_env_line("OPENAI_API_KEY=test-key") == ("OPENAI_API_KEY", "test-key")
    assert env_config._parse_env_line("# comment") is None
    assert env_config._parse_env_line("   ") is None


def test_load_project_env_reads_known_file(monkeypatch, tmp_path):
    env_file = tmp_path / "resolve_aio.env"
    env_file.write_text("OPENAI_API_KEY=file-key\n")
    monkeypatch.setattr(env_config, "ENV_FILES", [env_file])
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    loaded = env_config.load_project_env()

    assert loaded["OPENAI_API_KEY"] == "file-key"


def test_load_project_env_does_not_override_existing_env(monkeypatch, tmp_path):
    env_file = tmp_path / "resolve_aio.env"
    env_file.write_text("OPENAI_API_KEY=file-key\n")
    monkeypatch.setattr(env_config, "ENV_FILES", [env_file])
    monkeypatch.setenv("OPENAI_API_KEY", "system-key")

    loaded = env_config.load_project_env()

    assert loaded == {}
    assert env_config.os.environ["OPENAI_API_KEY"] == "system-key"
