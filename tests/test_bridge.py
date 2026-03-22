"""Tests for the Resolve Bridge module (offline — mocks the Resolve API)."""

from __future__ import annotations

import sys
from unittest.mock import ANY, MagicMock, patch

import pytest


# Mock the DaVinciResolveScript module before importing bridge
mock_dvr = MagicMock()
sys.modules["DaVinciResolveScript"] = mock_dvr


from src.mcp.resolve_bridge import ResolveBridge


@pytest.fixture
def bridge():
    b = ResolveBridge()
    # Create a mock Resolve object
    mock_resolve = MagicMock()
    mock_resolve.GetVersionString.return_value = "19.1.0"
    mock_resolve.GetCurrentPage.return_value = "edit"
    b._resolve = mock_resolve
    return b


@pytest.fixture
def bridge_with_project(bridge):
    mock_project = MagicMock()
    mock_project.GetName.return_value = "TestProject"
    mock_project.GetTimelineCount.return_value = 2
    mock_project.SaveProject.return_value = True

    mock_tl1 = MagicMock()
    mock_tl1.GetName.return_value = "Main Edit"
    mock_tl1.GetSetting.side_effect = lambda k: {
        "timelineFrameRate": "24",
        "timelineResolutionWidth": "1920",
        "timelineResolutionHeight": "1080",
    }.get(k, "")

    mock_tl2 = MagicMock()
    mock_tl2.GetName.return_value = "B-Roll"
    mock_tl2.GetSetting.side_effect = lambda k: {
        "timelineFrameRate": "30",
        "timelineResolutionWidth": "3840",
        "timelineResolutionHeight": "2160",
    }.get(k, "")

    mock_project.GetTimelineByIndex.side_effect = lambda i: {1: mock_tl1, 2: mock_tl2}.get(i)
    mock_project.GetCurrentTimeline.return_value = mock_tl1

    mock_pm = MagicMock()
    mock_pm.GetCurrentProject.return_value = mock_project
    mock_pm.GetProjectListInCurrentFolder.return_value = ["TestProject", "OtherProject"]
    bridge._resolve.GetProjectManager.return_value = mock_pm

    return bridge


class TestConnection:
    def test_connected_when_resolve_set(self, bridge):
        assert bridge.connected is True

    def test_not_connected_when_none(self):
        b = ResolveBridge()
        assert b.connected is False

    def test_require_raises_when_disconnected(self):
        b = ResolveBridge()
        with pytest.raises(RuntimeError, match="Not connected"):
            b._require()


class TestGeneral:
    def test_get_version(self, bridge):
        assert bridge.get_version() == "19.1.0"

    def test_get_current_page(self, bridge):
        assert bridge.get_current_page() == "edit"

    def test_set_current_page_valid(self, bridge):
        bridge._resolve.OpenPage.return_value = True
        assert bridge.set_current_page("color") is True

    def test_set_current_page_invalid(self, bridge):
        with pytest.raises(ValueError, match="Invalid page"):
            bridge.set_current_page("invalid")


class TestProjects:
    def test_list_projects(self, bridge_with_project):
        projects = bridge_with_project.list_projects()
        assert projects == ["TestProject", "OtherProject"]

    def test_get_current_project_name(self, bridge_with_project):
        assert bridge_with_project.get_current_project_name() == "TestProject"

    def test_save_project(self, bridge_with_project):
        assert bridge_with_project.save_project() is True


class TestTimelines:
    def test_list_timelines(self, bridge_with_project):
        timelines = bridge_with_project.list_timelines()
        assert len(timelines) == 2
        assert timelines[0]["name"] == "Main Edit"
        assert timelines[0]["frame_rate"] == "24"
        assert timelines[1]["name"] == "B-Roll"
        assert timelines[1]["resolution"] == "3840x2160"

    def test_get_current_timeline_name(self, bridge_with_project):
        assert bridge_with_project.get_current_timeline_name() == "Main Edit"

    def test_apply_grade_from_drx(self, bridge_with_project):
        timeline = bridge_with_project.get_current_timeline()
        item = MagicMock()
        timeline.ApplyGradeFromDRX.return_value = True
        bridge_with_project.get_timeline_items = MagicMock(return_value=[item])

        ok = bridge_with_project.apply_grade_from_drx("/tmp/look.drx")

        assert ok is True
        timeline.ApplyGradeFromDRX.assert_called_once_with("/tmp/look.drx", 0, [item])


class TestGallery:
    def test_list_gallery_albums(self, bridge_with_project):
        project = bridge_with_project.get_current_project()
        gallery = MagicMock()
        album_a = MagicMock()
        album_b = MagicMock()
        gallery.GetGalleryStillAlbums.return_value = [album_a, album_b]
        gallery.GetAlbumName.side_effect = lambda album: {
            album_a: "PowerGrades",
            album_b: "Client Looks",
        }[album]
        project.GetGallery.return_value = gallery

        albums = bridge_with_project.list_gallery_albums()

        assert albums == ["PowerGrades", "Client Looks"]

    def test_export_stills_uses_current_album(self, bridge_with_project, tmp_path):
        project = bridge_with_project.get_current_project()
        gallery = MagicMock()
        album = MagicMock()
        album.ExportStills.return_value = True
        gallery.GetCurrentStillAlbum.return_value = album
        project.GetGallery.return_value = gallery

        ok = bridge_with_project.export_stills([MagicMock()], str(tmp_path), "hero-look")

        assert ok is True
        album.ExportStills.assert_called_once_with([ANY], str(tmp_path), "hero-look", "drx")


class TestPresetManager:
    def test_type_map_covers_extensions(self):
        from src.automation.preset_manager import TYPE_MAP
        assert ".dctl" in TYPE_MAP
        assert ".cube" in TYPE_MAP
        assert ".3dl" in TYPE_MAP

    def test_get_bundled_presets_dir(self):
        from src.automation.preset_manager import get_bundled_presets_dir
        d = get_bundled_presets_dir()
        assert d.name == "presets"
