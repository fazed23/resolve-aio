"""
Rough Cut AI — Automated assembly edit.

Imports footage, creates a timeline, sorts clips, removes silence markers,
and builds an initial rough cut assembly.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from .silence_remover import detect_silent_segments, mark_silent_segments
from ..mcp.resolve_bridge import get_bridge

logger = logging.getLogger("resolve_aio.rough_cut")

MEDIA_EXTENSIONS = {
    ".mp4", ".mov", ".mxf", ".avi", ".mkv", ".m4v",
    ".r3d", ".braw", ".ari", ".dpx", ".exr",
    ".wav", ".aif", ".aiff", ".mp3", ".aac",
    ".jpg", ".jpeg", ".png", ".tif", ".tiff",
}


def scan_media_folder(folder: str) -> list[str]:
    """Find all supported media files in a folder (recursive)."""
    folder_path = Path(folder)
    if not folder_path.is_dir():
        raise FileNotFoundError(f"Folder not found: {folder}")

    files = []
    for f in folder_path.rglob("*"):
        if f.suffix.lower() in MEDIA_EXTENSIONS and not f.name.startswith("."):
            files.append(str(f))

    files.sort()
    logger.info("Found %d media files in %s", len(files), folder)
    return files


def create_rough_cut(
    source_folder: str = "",
    timeline_name: str = "Rough Cut v1",
    remove_silence: bool = True,
    sort_by_timecode: bool = True,
    color_tag: bool = False,
    add_markers: bool = False,
    file_paths: list[str] | None = None,
) -> dict:
    """
    Create a rough cut assembly from a folder or list of files.

    Returns a summary dict with counts and status.
    """
    bridge = get_bridge()
    if not bridge.connected:
        return {"error": "Not connected to DaVinci Resolve"}

    result = {
        "timeline": timeline_name,
        "imported": 0,
        "clips_added": 0,
        "markers_added": 0,
        "tagged": 0,
    }

    # Step 1: Import media
    if file_paths:
        media_files = file_paths
    elif source_folder:
        media_files = scan_media_folder(source_folder)
    else:
        # Use existing clips in Media Pool
        media_files = []

    if media_files:
        logger.info("Importing %d files...", len(media_files))
        clips = bridge.import_media(media_files)
        result["imported"] = len(clips) if clips else 0

    # Step 2: Create timeline
    logger.info("Creating timeline: %s", timeline_name)
    tl = bridge.create_timeline(timeline_name)
    if not tl:
        # Try to switch to existing one
        bridge.set_current_timeline(timeline_name)

    # Step 3: Get all clips from media pool and add to timeline
    pool_clips = bridge._media_pool().GetRootFolder().GetClipList()
    if pool_clips:
        # Sort by name (approximation of timecode sort)
        if sort_by_timecode:
            pool_clips_sorted = sorted(pool_clips, key=lambda c: c.GetName())
        else:
            pool_clips_sorted = list(pool_clips)

        added = bridge.append_to_timeline(pool_clips_sorted)
        result["clips_added"] = len(added) if added else 0

    # Step 4: Color tag by duration
    if color_tag:
        tl_items = bridge.get_timeline_items()
        tl_obj = bridge.get_current_timeline()
        fps_str = tl_obj.GetSetting("timelineFrameRate") if tl_obj else "24"
        fps = float(fps_str) if fps_str else 24.0

        for item in tl_items:
            try:
                start = item.GetStart()
                end = item.GetEnd()
                duration_sec = (end - start) / fps

                if duration_sec < 5.0:
                    bridge.set_clip_color(item, "Teal")  # B-roll
                elif duration_sec > 30.0:
                    bridge.set_clip_color(item, "Purple")  # Interviews
                else:
                    bridge.set_clip_color(item, "Blue")  # Medium
                result["tagged"] += 1
            except Exception:
                pass

    # Step 5: Add scene markers at clip boundaries
    if add_markers:
        tl_items = bridge.get_timeline_items()
        for i, item in enumerate(tl_items):
            try:
                frame = item.GetStart()
                name = item.GetName()
                ok = bridge.add_marker(frame, "Green", f"Scene {i+1}", name)
                if ok:
                    result["markers_added"] += 1
            except Exception:
                pass

    # Step 6: Mark potential silence regions when requested
    if remove_silence:
        silent_segments = detect_silent_segments()
        result["silent_segments"] = len(silent_segments)
        if silent_segments:
            result["markers_added"] += mark_silent_segments(
                silent_segments,
                color="Red",
                marker_note="Potential silence in rough cut",
            )
    else:
        result["silent_segments"] = 0

    # Step 7: Save
    bridge.save_project()

    logger.info("Rough cut complete: %s", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a rough cut assembly")
    parser.add_argument("--folder", default="", help="Source media folder")
    parser.add_argument("--name", default="Rough Cut v1", help="Timeline name")
    parser.add_argument("--no-silence", action="store_true", help="Skip silence removal")
    parser.add_argument("--no-sort", action="store_true", help="Don't sort by timecode")
    parser.add_argument("--color-tag", action="store_true", help="Color-tag by duration")
    parser.add_argument("--markers", action="store_true", help="Add scene markers")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    result = create_rough_cut(
        source_folder=args.folder,
        timeline_name=args.name,
        remove_silence=not args.no_silence,
        sort_by_timecode=not args.no_sort,
        color_tag=args.color_tag,
        add_markers=args.markers,
    )

    print(f"\nRough Cut Summary:")
    print(f"  Timeline: {result['timeline']}")
    print(f"  Imported: {result['imported']} files")
    print(f"  Clips added: {result['clips_added']}")
    print(f"  Markers: {result['markers_added']}")
    print(f"  Tagged: {result['tagged']}")


if __name__ == "__main__":
    main()
