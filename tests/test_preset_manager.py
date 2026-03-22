"""Tests for bundled preset discovery and installation helpers."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import pytest

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


def test_list_installed_presets_scans_all_existing_lut_dirs(monkeypatch, tmp_path):
    lut_a = tmp_path / "LUT_A"
    lut_b = tmp_path / "LUT_B"
    (lut_a / "ResolveAIO" / "creative").mkdir(parents=True)
    (lut_b / "ResolveAIO" / "limiters").mkdir(parents=True)
    (lut_a / "ResolveAIO" / "creative" / "Look.cube").write_text("lut")
    (lut_b / "ResolveAIO" / "limiters" / "Clamp.dctl").write_text("dctl")

    template_root = tmp_path / "Templates" / "Edit"
    (template_root / "Titles").mkdir(parents=True)
    (template_root / "Titles" / "TypewriterText.setting").write_text("setting")

    monkeypatch.setattr(preset_manager, "get_existing_lut_dirs", lambda: [lut_a, lut_b])
    monkeypatch.setattr(preset_manager, "get_lut_dir_candidates", lambda: [lut_a, lut_b])
    monkeypatch.setattr(
        preset_manager,
        "get_fusion_template_dir",
        lambda category="Titles": template_root / category,
    )

    presets = preset_manager.list_installed_presets()
    names = {preset["name"] for preset in presets}

    assert "Look.cube" in names
    assert "Clamp.dctl" in names
    assert "TypewriterText.setting" in names


def test_install_bundled_assets_strict_raises_on_partial_failure(monkeypatch, tmp_path):
    source = tmp_path / "TestLook.cube"
    source.write_text("lut")
    assets = [
        {
            "name": "Test Look",
            "file_name": source.name,
            "type": "LUT",
            "category": "looks",
            "description": "test",
            "path": str(source),
            "relative": "luts/TestLook.cube",
            "action": "apply",
        }
    ]

    monkeypatch.setattr(preset_manager, "list_bundled_assets", lambda asset_type=None: assets)
    monkeypatch.setattr(
        preset_manager,
        "install_preset",
        lambda source, category="": (_ for _ in ()).throw(PermissionError("no write access")),
    )

    with pytest.raises(RuntimeError) as exc:
        preset_manager.install_bundled_assets(strict=True)

    assert "Failed to install 1 asset" in str(exc.value)
