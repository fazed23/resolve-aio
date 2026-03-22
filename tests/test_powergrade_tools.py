"""Tests for PowerGrade export and apply helpers."""

from __future__ import annotations

from pathlib import Path

from src.automation import powergrade_tools


class FakeBridge:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.apply_calls: list[tuple[str, int, int]] = []

    def list_gallery_albums(self) -> list[str]:
        return ["PowerGrades", "Client Looks"]

    def import_stills(self, file_paths: list[str], album_name: str | None = None) -> bool:
        return file_paths == ["/tmp/look.drx"] and album_name == "PowerGrades"

    def apply_grade_from_drx(self, path: str, grade_mode: int = 0, track_index: int = 1) -> bool:
        self.apply_calls.append((path, grade_mode, track_index))
        return True

    def grab_still(self) -> object:
        return object()

    def export_stills(self, stills, folder_path: str, file_prefix: str, fmt: str = "drx", album_name: str | None = None) -> bool:
        count = len(stills)
        for index in range(1, count + 1):
            Path(folder_path, f"{file_prefix}_{index:03d}.drx").write_text(f"still-{index}")
        return True

    def get_current_timeline_name(self) -> str:
        return "Main Edit"

    def grab_all_stills(self, still_frame_source: int = 2) -> list[object]:
        return [object(), object()]


def test_list_gallery_albums(monkeypatch, tmp_path):
    monkeypatch.setattr(powergrade_tools, "get_bridge", lambda: FakeBridge(tmp_path))

    albums = powergrade_tools.list_gallery_albums()

    assert albums == ["PowerGrades", "Client Looks"]


def test_import_powergrade(monkeypatch, tmp_path):
    monkeypatch.setattr(powergrade_tools, "get_bridge", lambda: FakeBridge(tmp_path))

    ok = powergrade_tools.import_powergrade("/tmp/look.drx", album_name="PowerGrades")

    assert ok is True


def test_apply_powergrade_to_all_clips(monkeypatch, tmp_path):
    bridge = FakeBridge(tmp_path)
    monkeypatch.setattr(powergrade_tools, "get_bridge", lambda: bridge)

    ok = powergrade_tools.apply_powergrade_to_all_clips("/tmp/look.drx", grade_mode=2, track_index=3)

    assert ok is True
    assert bridge.apply_calls == [("/tmp/look.drx", 2, 3)]


def test_export_current_powergrade_renames_export(monkeypatch, tmp_path):
    monkeypatch.setattr(powergrade_tools, "get_bridge", lambda: FakeBridge(tmp_path))

    exported = powergrade_tools.export_current_powergrade("Hero Look", output_dir=tmp_path)

    assert exported == str(tmp_path / "hero-look.drx")
    assert (tmp_path / "hero-look.drx").exists()


def test_export_timeline_powergrades_collects_new_files(monkeypatch, tmp_path):
    monkeypatch.setattr(powergrade_tools, "get_bridge", lambda: FakeBridge(tmp_path))

    exported = powergrade_tools.export_timeline_powergrades(output_dir=tmp_path, prefix="main-edit")

    assert len(exported) == 2
    assert exported[0].endswith("main-edit_001.drx")
