"""
PowerGrade Tools — export, import, and apply real Resolve DRX files.

These helpers rely on the DaVinci Resolve Gallery API, so Resolve must be open
and scripting access must be available when they run.
"""

from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path

from ..mcp.resolve_bridge import get_bridge

logger = logging.getLogger("resolve_aio.powergrade_tools")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_POWERGRADE_DIR = PROJECT_ROOT / "presets" / "powergrades"
FRAME_SOURCES = {"first": 1, "middle": 2}
GRADE_MODES = {
    "no-keyframes": 0,
    "source-timecode": 1,
    "start-frames": 2,
}


def _slugify(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "-", value.strip()).strip("-").lower()
    return text or "powergrade"


def _new_files(folder: Path, pattern: str, before: set[str]) -> list[Path]:
    return sorted(
        [path for path in folder.glob(pattern) if path.name not in before],
        key=lambda path: (path.stat().st_mtime, path.name),
    )


def list_gallery_albums() -> list[str]:
    """Return Resolve Gallery album names."""
    return get_bridge().list_gallery_albums()


def import_powergrade(path: str, album_name: str | None = None) -> bool:
    """Import a DRX file into the current or specified gallery album."""
    return get_bridge().import_stills([path], album_name=album_name)


def apply_powergrade_to_all_clips(
    path: str,
    grade_mode: int = 0,
    track_index: int = 1,
) -> bool:
    """Apply a DRX PowerGrade to every clip on a video track."""
    return get_bridge().apply_grade_from_drx(path, grade_mode=grade_mode, track_index=track_index)


def export_current_powergrade(
    name: str,
    output_dir: str | Path | None = None,
    album_name: str | None = None,
) -> str:
    """Grab the current clip grade and export it as a single DRX file."""
    bridge = get_bridge()
    target_dir = Path(output_dir) if output_dir else DEFAULT_POWERGRADE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    stem = _slugify(name)
    dest = target_dir / f"{stem}.drx"
    before = {path.name for path in target_dir.glob(f"{stem}*.drx")}
    still = bridge.grab_still()
    ok = bridge.export_stills([still], str(target_dir), stem, fmt="drx", album_name=album_name)
    if not ok:
        raise RuntimeError("Resolve failed to export the PowerGrade")

    exported = _new_files(target_dir, f"{stem}*.drx", before)
    if not exported:
        raise RuntimeError("Resolve did not create a DRX file")

    primary = exported[0]
    if primary != dest:
        if dest.exists():
            dest.unlink()
        primary.replace(dest)
    return str(dest)


def export_timeline_powergrades(
    output_dir: str | Path | None = None,
    prefix: str | None = None,
    album_name: str | None = None,
    frame_source: str = "middle",
) -> list[str]:
    """Grab stills from all clips on the current timeline and export them as DRX files."""
    bridge = get_bridge()
    timeline_name = bridge.get_current_timeline_name() or "timeline"
    target_dir = Path(output_dir) if output_dir else DEFAULT_POWERGRADE_DIR / _slugify(timeline_name)
    target_dir.mkdir(parents=True, exist_ok=True)

    source_value = FRAME_SOURCES[frame_source]
    file_prefix = _slugify(prefix or timeline_name)
    before = {path.name for path in target_dir.glob(f"{file_prefix}*.drx")}
    stills = bridge.grab_all_stills(source_value)
    if not stills:
        return []

    ok = bridge.export_stills(stills, str(target_dir), file_prefix, fmt="drx", album_name=album_name)
    if not ok:
        raise RuntimeError("Resolve failed to export timeline PowerGrades")

    exported = _new_files(target_dir, f"{file_prefix}*.drx", before)
    return [str(path) for path in exported]


def main() -> None:
    parser = argparse.ArgumentParser(description="Export and apply Resolve DRX PowerGrades")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list-albums", help="List Resolve gallery albums")

    export_current = sub.add_parser("export-current", help="Export the current clip grade as a DRX file")
    export_current.add_argument("name", help="Output PowerGrade name")
    export_current.add_argument("--output-dir", default="", help="Destination folder")
    export_current.add_argument("--album", default="", help="Gallery album to export from")

    export_timeline = sub.add_parser("export-timeline", help="Export DRX files for all clips in the current timeline")
    export_timeline.add_argument("--output-dir", default="", help="Destination folder")
    export_timeline.add_argument("--prefix", default="", help="Filename prefix")
    export_timeline.add_argument("--album", default="", help="Gallery album to export from")
    export_timeline.add_argument(
        "--frame-source",
        choices=sorted(FRAME_SOURCES),
        default="middle",
        help="Grab the first or middle frame from each clip",
    )

    import_cmd = sub.add_parser("import", help="Import a DRX file into Resolve's gallery")
    import_cmd.add_argument("path", help="Path to a .drx file")
    import_cmd.add_argument("--album", default="", help="Gallery album to import into")

    apply_cmd = sub.add_parser("apply", help="Apply a DRX file to all clips on the current timeline")
    apply_cmd.add_argument("path", help="Path to a .drx file")
    apply_cmd.add_argument("--track", type=int, default=1, help="Video track index")
    apply_cmd.add_argument(
        "--mode",
        choices=sorted(GRADE_MODES),
        default="no-keyframes",
        help="Resolve grade alignment mode",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    if args.command == "list-albums":
        albums = list_gallery_albums()
        for album in albums:
            print(f"  • {album}")
        print(f"\nTotal: {len(albums)} albums")
    elif args.command == "export-current":
        exported = export_current_powergrade(
            args.name,
            output_dir=args.output_dir or None,
            album_name=args.album or None,
        )
        print(f"Exported: {exported}")
    elif args.command == "export-timeline":
        exported = export_timeline_powergrades(
            output_dir=args.output_dir or None,
            prefix=args.prefix or None,
            album_name=args.album or None,
            frame_source=args.frame_source,
        )
        if exported:
            print("Exported:")
            for path in exported:
                print(f"  • {path}")
        else:
            print("No DRX files were exported")
    elif args.command == "import":
        ok = import_powergrade(args.path, album_name=args.album or None)
        print("Imported" if ok else "Import failed")
    elif args.command == "apply":
        ok = apply_powergrade_to_all_clips(
            args.path,
            grade_mode=GRADE_MODES[args.mode],
            track_index=args.track,
        )
        print("Applied" if ok else "Apply failed")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
