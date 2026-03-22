"""
Resolve Bridge — unified wrapper around the DaVinci Resolve Scripting API.

All MCP tools and automation scripts go through this module to talk to Resolve.
It handles discovery, connection, reconnection, and exposes a clean Python API.
"""

from __future__ import annotations

import logging
import os
import platform
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("resolve_aio.bridge")


def _resolve_script_paths() -> tuple[str, str]:
    """Return (RESOLVE_SCRIPT_API, RESOLVE_SCRIPT_LIB) for the current OS."""
    system = platform.system()

    if system == "Darwin":
        api = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
        lib = (
            "/Applications/DaVinci Resolve/DaVinci Resolve.app"
            "/Contents/Libraries/Fusion/fusionscript.so"
        )
    elif system == "Windows":
        prog = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
        api = (
            rf"{prog}\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting"
        )
        lib = (
            rf"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"
        )
    elif system == "Linux":
        api = "/opt/resolve/Developer/Scripting"
        lib = "/opt/resolve/libs/Fusion/fusionscript.so"
    else:
        raise RuntimeError(f"Unsupported platform: {system}")

    return (
        os.environ.get("RESOLVE_SCRIPT_API", api),
        os.environ.get("RESOLVE_SCRIPT_LIB", lib),
    )


def _ensure_python_path() -> None:
    """Add Resolve's scripting modules to sys.path if not already present."""
    api_path, _ = _resolve_script_paths()
    modules_dir = os.path.join(api_path, "Modules")
    if modules_dir not in sys.path:
        sys.path.insert(0, modules_dir)


class ResolveBridge:
    """Thin, reconnectable wrapper around the Resolve scripting API."""

    def __init__(self) -> None:
        self._resolve: Any = None
        self._fusion: Any = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Attempt to connect to a running Resolve instance. Returns True on success."""
        _ensure_python_path()
        try:
            import DaVinciResolveScript as dvr  # type: ignore[import-untyped]

            self._resolve = dvr.scriptapp("Resolve")
            self._fusion = dvr.scriptapp("Fusion")
            if self._resolve is None:
                logger.warning("Resolve scripting returned None — is Resolve running?")
                return False
            logger.info("Connected to DaVinci Resolve")
            return True
        except ImportError:
            logger.error(
                "Cannot import DaVinciResolveScript. "
                "Check RESOLVE_SCRIPT_API / PYTHONPATH."
            )
            return False
        except Exception as exc:
            logger.error("Failed to connect to Resolve: %s", exc)
            return False

    @property
    def connected(self) -> bool:
        return self._resolve is not None

    def _require(self) -> Any:
        if not self.connected:
            raise RuntimeError("Not connected to DaVinci Resolve")
        return self._resolve

    # ------------------------------------------------------------------
    # General
    # ------------------------------------------------------------------

    def get_version(self) -> str:
        r = self._require()
        return r.GetVersionString()

    def get_current_page(self) -> str:
        r = self._require()
        return r.GetCurrentPage()

    def set_current_page(self, page: str) -> bool:
        valid = {"media", "cut", "edit", "fusion", "color", "fairlight", "deliver"}
        if page.lower() not in valid:
            raise ValueError(f"Invalid page '{page}'. Must be one of {valid}")
        r = self._require()
        return r.OpenPage(page.lower())

    # ------------------------------------------------------------------
    # Project Manager
    # ------------------------------------------------------------------

    def _pm(self) -> Any:
        return self._require().GetProjectManager()

    def list_projects(self) -> list[str]:
        pm = self._pm()
        return pm.GetProjectListInCurrentFolder()

    def get_current_project(self) -> Any:
        return self._pm().GetCurrentProject()

    def get_current_project_name(self) -> str:
        proj = self.get_current_project()
        return proj.GetName() if proj else ""

    def open_project(self, name: str) -> bool:
        return self._pm().LoadProject(name)

    def create_project(self, name: str) -> Any | None:
        return self._pm().CreateProject(name)

    def save_project(self) -> bool:
        proj = self.get_current_project()
        return proj.SaveProject() if proj else False

    def close_project(self) -> bool:
        return self._pm().CloseProject(self.get_current_project())

    # ------------------------------------------------------------------
    # Database / Folder
    # ------------------------------------------------------------------

    def list_databases(self) -> list[dict[str, str]]:
        pm = self._pm()
        return pm.GetDatabaseList()

    def get_current_folder(self) -> str:
        pm = self._pm()
        return pm.GetCurrentFolder()

    def list_folders(self) -> list[str]:
        pm = self._pm()
        return pm.GetFolderListInCurrentFolder()

    def open_folder(self, name: str) -> bool:
        return self._pm().OpenFolder(name)

    # ------------------------------------------------------------------
    # Timeline
    # ------------------------------------------------------------------

    def _project(self) -> Any:
        proj = self.get_current_project()
        if not proj:
            raise RuntimeError("No project is currently open")
        return proj

    def list_timelines(self) -> list[dict[str, Any]]:
        proj = self._project()
        count = proj.GetTimelineCount()
        timelines = []
        for i in range(1, count + 1):
            tl = proj.GetTimelineByIndex(i)
            if tl:
                timelines.append({
                    "index": i,
                    "name": tl.GetName(),
                    "frame_rate": tl.GetSetting("timelineFrameRate"),
                    "resolution": f"{tl.GetSetting('timelineResolutionWidth')}x{tl.GetSetting('timelineResolutionHeight')}",
                })
        return timelines

    def get_current_timeline(self) -> Any | None:
        return self._project().GetCurrentTimeline()

    def get_current_timeline_name(self) -> str:
        tl = self.get_current_timeline()
        return tl.GetName() if tl else ""

    def set_current_timeline(self, name: str) -> bool:
        proj = self._project()
        count = proj.GetTimelineCount()
        for i in range(1, count + 1):
            tl = proj.GetTimelineByIndex(i)
            if tl and tl.GetName() == name:
                return proj.SetCurrentTimeline(tl)
        return False

    def create_timeline(self, name: str) -> Any | None:
        mp = self._project().GetMediaPool()
        return mp.CreateEmptyTimeline(name)

    def delete_timeline(self, name: str) -> bool:
        proj = self._project()
        count = proj.GetTimelineCount()
        for i in range(1, count + 1):
            tl = proj.GetTimelineByIndex(i)
            if tl and tl.GetName() == name:
                return proj.DeleteTimeline(tl)
        return False

    # ------------------------------------------------------------------
    # Timeline — Markers
    # ------------------------------------------------------------------

    def get_markers(self) -> dict[int, dict]:
        tl = self.get_current_timeline()
        return tl.GetMarkers() if tl else {}

    def add_marker(
        self,
        frame: int,
        color: str = "Blue",
        name: str = "",
        note: str = "",
        duration: int = 1,
    ) -> bool:
        tl = self.get_current_timeline()
        if not tl:
            return False
        return tl.AddMarker(frame, color, name, note, duration)

    def delete_marker(self, frame: int) -> bool:
        tl = self.get_current_timeline()
        if not tl:
            return False
        return tl.DeleteMarkerAtFrame(frame)

    def get_current_timecode(self) -> str:
        tl = self.get_current_timeline()
        return tl.GetCurrentTimecode() if tl else ""

    # ------------------------------------------------------------------
    # Media Pool
    # ------------------------------------------------------------------

    def _media_pool(self) -> Any:
        return self._project().GetMediaPool()

    def _root_folder(self) -> Any:
        return self._media_pool().GetRootFolder()

    def list_clips(self, folder: Any | None = None) -> list[dict[str, Any]]:
        folder = folder or self._root_folder()
        clips = folder.GetClipList()
        result = []
        for clip in clips:
            result.append({
                "name": clip.GetName(),
                "duration": clip.GetClipProperty("Duration"),
                "fps": clip.GetClipProperty("FPS"),
                "resolution": clip.GetClipProperty("Resolution"),
                "file_path": clip.GetClipProperty("File Path"),
            })
        return result

    def list_bins(self, folder: Any | None = None) -> list[str]:
        folder = folder or self._root_folder()
        return [sf.GetName() for sf in folder.GetSubFolderList()]

    def create_bin(self, name: str) -> Any | None:
        mp = self._media_pool()
        return mp.AddSubFolder(mp.GetCurrentFolder(), name)

    def set_current_bin(self, name: str) -> bool:
        mp = self._media_pool()
        root = mp.GetRootFolder()
        for sf in root.GetSubFolderList():
            if sf.GetName() == name:
                return mp.SetCurrentFolder(sf)
        return False

    def import_media(self, file_paths: list[str]) -> list[Any]:
        mp = self._media_pool()
        return mp.ImportMedia(file_paths)

    def append_to_timeline(self, clips: list[Any]) -> list[Any]:
        mp = self._media_pool()
        return mp.AppendToTimeline(clips)

    # ------------------------------------------------------------------
    # Color Page
    # ------------------------------------------------------------------

    def get_timeline_items(self, track_index: int = 1) -> list[Any]:
        tl = self.get_current_timeline()
        if not tl:
            return []
        return tl.GetItemListInTrack("video", track_index)

    def get_clip_color_info(self, item: Any) -> dict[str, Any]:
        return {
            "name": item.GetName(),
            "color_group": item.GetClipColor(),
            "node_count": item.GetNumNodes() if hasattr(item, "GetNumNodes") else None,
        }

    def set_clip_color(self, item: Any, color: str) -> bool:
        return item.SetClipColor(color)

    def get_current_node(self, item: Any) -> int:
        return item.GetCurrentNode() if hasattr(item, "GetCurrentNode") else 1

    def add_node(self, item: Any) -> bool:
        if hasattr(item, "AddNode"):
            return item.AddNode()
        return False

    def apply_lut(self, item: Any, lut_path: str, node_index: int = 1) -> bool:
        if hasattr(item, "SetLUT"):
            return item.SetLUT(node_index, {"1": lut_path})
        return False

    def apply_grade_from_drx(
        self,
        drx_path: str,
        grade_mode: int = 0,
        track_index: int = 1,
    ) -> bool:
        """Apply a DRX PowerGrade to all clips on a video track."""
        tl = self.get_current_timeline()
        if not tl:
            return False
        items = self.get_timeline_items(track_index)
        if not items:
            return False
        return tl.ApplyGradeFromDRX(str(drx_path), grade_mode, items)

    # ------------------------------------------------------------------
    # Gallery / PowerGrades
    # ------------------------------------------------------------------

    def _gallery(self) -> Any:
        proj = self._project()
        if not hasattr(proj, "GetGallery"):
            raise RuntimeError("Gallery API is not available in this Resolve build")
        gallery = proj.GetGallery()
        if gallery is None:
            raise RuntimeError("Could not access the Resolve gallery")
        return gallery

    def _current_still_album(self) -> Any:
        gallery = self._gallery()
        album = gallery.GetCurrentStillAlbum()
        if album is None:
            raise RuntimeError("No current gallery still album is available")
        return album

    def list_gallery_albums(self) -> list[str]:
        gallery = self._gallery()
        names: list[str] = []
        for album in gallery.GetGalleryStillAlbums() or []:
            try:
                names.append(gallery.GetAlbumName(album))
            except Exception:
                continue
        return names

    def get_current_gallery_album_name(self) -> str:
        gallery = self._gallery()
        album = gallery.GetCurrentStillAlbum()
        if album is None:
            return ""
        return gallery.GetAlbumName(album)

    def set_current_gallery_album(self, name: str) -> bool:
        gallery = self._gallery()
        for album in gallery.GetGalleryStillAlbums() or []:
            if gallery.GetAlbumName(album) == name:
                return gallery.SetCurrentStillAlbum(album)
        return False

    def grab_still(self) -> Any:
        tl = self.get_current_timeline()
        if not tl:
            raise RuntimeError("No active timeline to grab a still from")
        still = tl.GrabStill()
        if still is None:
            raise RuntimeError("Resolve could not grab a still from the current clip")
        return still

    def grab_all_stills(self, still_frame_source: int = 2) -> list[Any]:
        tl = self.get_current_timeline()
        if not tl:
            raise RuntimeError("No active timeline to grab stills from")
        stills = tl.GrabAllStills(still_frame_source) or []
        return list(stills)

    def import_stills(self, file_paths: list[str], album_name: str | None = None) -> bool:
        if album_name and not self.set_current_gallery_album(album_name):
            raise RuntimeError(f"Gallery album not found: {album_name}")
        album = self._current_still_album()
        return album.ImportStills([str(Path(path)) for path in file_paths])

    def export_stills(
        self,
        stills: list[Any],
        folder_path: str,
        file_prefix: str,
        fmt: str = "drx",
        album_name: str | None = None,
    ) -> bool:
        if album_name and not self.set_current_gallery_album(album_name):
            raise RuntimeError(f"Gallery album not found: {album_name}")
        album = self._current_still_album()
        folder = Path(folder_path)
        folder.mkdir(parents=True, exist_ok=True)
        return album.ExportStills(stills, str(folder), file_prefix, fmt)

    # ------------------------------------------------------------------
    # Render / Deliver
    # ------------------------------------------------------------------

    def get_render_presets(self) -> list[str]:
        proj = self._project()
        return proj.GetRenderPresetList()

    def set_render_preset(self, name: str) -> bool:
        proj = self._project()
        return proj.LoadRenderPreset(name)

    def set_render_settings(self, settings: dict[str, Any]) -> bool:
        proj = self._project()
        return proj.SetRenderSettings(settings)

    def add_render_job(self) -> str:
        proj = self._project()
        return proj.AddRenderJob()

    def start_render(self) -> bool:
        proj = self._project()
        return proj.StartRendering()

    def get_render_status(self) -> dict[str, Any]:
        proj = self._project()
        return {
            "is_rendering": proj.IsRenderingInProgress(),
            "jobs": proj.GetRenderJobList(),
        }

    def stop_render(self) -> None:
        self._project().StopRendering()

    # ------------------------------------------------------------------
    # Fusion
    # ------------------------------------------------------------------

    def get_fusion_comp(self) -> Any | None:
        tl = self.get_current_timeline()
        if not tl:
            return None
        items = tl.GetItemListInTrack("video", 1)
        if items:
            return items[0].GetFusionCompByIndex(1)
        return None

    def list_fusion_tools(self, comp: Any | None = None) -> list[str]:
        comp = comp or self.get_fusion_comp()
        if not comp:
            return []
        tools = comp.GetToolList()
        return [t.GetAttrs()["TOOLS_Name"] for t in tools.values()]


# Module-level singleton
_bridge: ResolveBridge | None = None


def get_bridge() -> ResolveBridge:
    """Get or create the global ResolveBridge singleton."""
    global _bridge
    if _bridge is None:
        _bridge = ResolveBridge()
        _bridge.connect()
    return _bridge
