"""Tests for bundled preset discovery and installation helpers."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from src.automation import preset_manager


def test_list_bundled_assets_includes_real_files():
    assets = preset_manager.list_bundled_assets()
    counts = Counter(asset["type"] for asset in assets)
    template_categories = Counter(
        asset["category"] for asset in assets if asset["type"] == "FusionTemplate"
    )

    assert counts["DCTL"] >= 20
    assert counts["LUT"] >= 6
    assert counts["FusionTemplate"] >= 26
    assert template_categories["Titles"] >= 20
    assert template_categories["Transitions"] >= 6


def test_find_bundled_asset_by_display_name():
    asset = preset_manager.find_bundled_asset("Kodak 2383 Print")

    assert asset is not None
    assert asset["type"] == "LUT"
    assert asset["file_name"] == "Kodak2383Print.cube"


def test_install_lut_uses_lut_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(preset_manager, "get_lut_dir", lambda: tmp_path / "LUT")
    asset = preset_manager.find_bundled_asset("Fuji 3513 Print")

    dest = preset_manager.install_preset(asset["path"], category=asset["category"])

    assert Path(dest).exists()
    assert Path(dest).name == "Fuji3513Print.cube"


def test_install_fusion_template_uses_template_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(
        preset_manager,
        "get_fusion_template_dir",
        lambda category="Titles": tmp_path / "Templates" / category,
    )
    asset = preset_manager.find_bundled_asset("Typewriter", asset_type="FusionTemplate")

    dest = preset_manager.install_preset(asset["path"], category=asset["category"])

    assert Path(dest).exists()
    assert Path(dest).name == "TypewriterText.setting"


def test_install_powergrade_raises_clear_error(tmp_path):
    drx = tmp_path / "look.drx"
    drx.write_text("fake")

    try:
        preset_manager.install_preset(str(drx))
    except ValueError as exc:
        assert "PowerGrade .drx files are not installed" in str(exc)
    else:
        raise AssertionError("Expected install_preset to reject .drx installation")
