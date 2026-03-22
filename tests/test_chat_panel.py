"""Tests for the chat panel command routing."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.ui import chat_panel
from src.ui.chat_panel import _create_ai_engine, process_command


class FakeAIEngine:
    def __init__(self, response: str):
        self.response = response
        self.calls: list[str] = []

    async def chat(self, text: str) -> str:
        self.calls.append(text)
        return self.response


def test_create_ai_engine_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert _create_ai_engine(MagicMock()) is None


@pytest.mark.asyncio
async def test_process_command_prefers_builtin_rules():
    bridge = MagicMock()
    bridge.get_version.return_value = "19.1.0"
    bridge.get_current_project_name.return_value = "Demo"
    bridge.get_current_timeline_name.return_value = "Main Edit"
    bridge.get_current_page.return_value = "edit"
    ai_engine = FakeAIEngine("AI fallback")

    response = await process_command(bridge, "version", ai_engine=ai_engine)

    assert "DaVinci Resolve 19.1.0" in response
    assert ai_engine.calls == []


@pytest.mark.asyncio
async def test_process_command_uses_ai_for_unmatched_input():
    ai_engine = FakeAIEngine("AI handled it")

    response = await process_command(MagicMock(), "make this timeline more cinematic", ai_engine=ai_engine)

    assert response == "AI handled it"
    assert ai_engine.calls == ["make this timeline more cinematic"]


@pytest.mark.asyncio
async def test_process_command_falls_back_to_help_when_ai_fails():
    ai_engine = FakeAIEngine("AI Error: upstream unavailable")

    response = await process_command(MagicMock(), "unmatched command", ai_engine=ai_engine)

    assert "Some things you can try" in response


@pytest.mark.asyncio
async def test_process_command_applies_bundled_preset(monkeypatch):
    monkeypatch.setattr(
        "src.automation.auto_grade.apply_lut_to_all_clips",
        lambda path, node_index=1, track_index=1, skip_already_graded=True: {"Clip A": True, "Clip B": True},
    )

    response = await process_command(MagicMock(), 'apply preset "Kodak 2383 Print"')

    assert "Applied Kodak 2383 Print to 2/2 clips." in response


@pytest.mark.asyncio
async def test_process_command_applies_bundled_powergrade(monkeypatch):
    monkeypatch.setattr(
        chat_panel,
        "find_bundled_asset",
        lambda name, asset_type=None: {
            "name": "Hero Look",
            "type": "PowerGrade",
            "path": "/tmp/hero-look.drx",
            "relative": "powergrades/hero-look.drx",
            "category": "powergrades",
        },
    )
    monkeypatch.setattr(chat_panel, "apply_powergrade_to_all_clips", lambda path: True)

    response = await process_command(MagicMock(), 'apply preset "Hero Look"')

    assert "Applied PowerGrade Hero Look." in response


@pytest.mark.asyncio
async def test_process_command_installs_text_animation(monkeypatch, tmp_path):
    monkeypatch.setattr(chat_panel, "install_preset", lambda path, category="": str(tmp_path / category / Path(path).name))

    response = await process_command(MagicMock(), 'install text animation "Typewriter"')

    assert "Installed text animation: Typewriter" in response


@pytest.mark.asyncio
async def test_process_command_installs_transition(monkeypatch, tmp_path):
    monkeypatch.setattr(
        chat_panel,
        "find_bundled_asset",
        lambda name, asset_type=None: {
            "name": "Whip Slide",
            "type": "FusionTemplate",
            "path": "/tmp/WhipSlide.setting",
            "relative": "fusion_templates/Transitions/WhipSlide.setting",
            "category": "Transitions",
        },
    )
    monkeypatch.setattr(chat_panel, "install_preset", lambda path, category="": str(tmp_path / category / Path(path).name))

    response = await process_command(MagicMock(), 'install transition "Whip Slide"')

    assert "Installed transition: Whip Slide" in response


@pytest.mark.asyncio
async def test_process_command_exports_current_powergrade(monkeypatch):
    bridge = MagicMock()
    bridge.get_current_timeline_name.return_value = "Main Edit"
    monkeypatch.setattr(chat_panel, "export_current_powergrade", lambda name: "/tmp/main-edit.drx")

    response = await process_command(bridge, 'export current powergrade "Main Edit"')

    assert "Exported PowerGrade: /tmp/main-edit.drx" == response


@pytest.mark.asyncio
async def test_process_command_marks_silence(monkeypatch):
    monkeypatch.setattr("src.automation.silence_remover.detect_silent_segments", lambda: [{"start_frame": 10, "end_frame": 20, "duration_sec": 0.4}])
    monkeypatch.setattr("src.automation.silence_remover.mark_silent_segments", lambda segments: len(segments))

    response = await process_command(MagicMock(), "remove silence")

    assert "Detected 1 potential silent segments." in response
    assert "Added 1 silence markers" in response


@pytest.mark.asyncio
async def test_process_command_color_tags_clips(monkeypatch):
    monkeypatch.setattr(
        "src.automation.auto_grade.color_tag_by_duration",
        lambda: {"Clip A": "Teal", "Clip B": "Blue", "Clip C": "Blue"},
    )

    response = await process_command(MagicMock(), "color tag clips by duration")

    assert "Tagged 3 clips by duration." in response
    assert "Blue=2" in response
    assert "Teal=1" in response


@pytest.mark.asyncio
async def test_process_command_creates_rough_cut(monkeypatch):
    monkeypatch.setattr(
        "src.automation.rough_cut.create_rough_cut",
        lambda **kwargs: {
            "timeline": kwargs["timeline_name"],
            "imported": 0,
            "clips_added": 5,
            "markers_added": 2,
            "tagged": 1,
            "silent_segments": 2,
        },
    )

    response = await process_command(
        MagicMock(),
        'create rough cut "Assembly 01" with options: remove silence, add scene markers',
    )

    assert "Rough cut created: Assembly 01" in response
    assert "Clips added: 5" in response
    assert "Silent segments: 2" in response


@pytest.mark.asyncio
async def test_process_command_runs_batch_render(monkeypatch):
    monkeypatch.setattr(
        "src.automation.batch_render.render_all_timelines",
        lambda: {"Main Edit": True, "Social Cut": False},
    )

    response = await process_command(MagicMock(), "batch render all timelines")

    assert "Queued/rendered 1/2 timelines." in response
    assert "Main Edit: OK" in response
