"""
Auto Grade — Applies a base color grade to all clips on a timeline.

Supports:
  - Applying a LUT/DCTL to all clips
  - Shot matching based on a reference clip
  - Setting clip colors by type (interviews, b-roll, etc.)
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from ..mcp.resolve_bridge import get_bridge

logger = logging.getLogger("resolve_aio.auto_grade")


def apply_lut_to_all_clips(
    lut_path: str,
    node_index: int = 1,
    track_index: int = 1,
    skip_already_graded: bool = True,
) -> dict[str, bool]:
    """Apply a LUT or DCTL to all clips on a video track."""
    bridge = get_bridge()
    items = bridge.get_timeline_items(track_index)

    results: dict[str, bool] = {}
    for item in items:
        name = item.GetName()

        if skip_already_graded:
            # Check if clip already has a LUT on this node
            existing = item.GetLUT(node_index) if hasattr(item, "GetLUT") else None
            if existing:
                logger.info("Skipping %s (already graded on node %d)", name, node_index)
                results[name] = True
                continue

        ok = bridge.apply_lut(item, lut_path, node_index)
        results[name] = ok
        if ok:
            logger.info("Applied LUT to %s", name)
        else:
            logger.warning("Failed to apply LUT to %s", name)

    return results


def color_tag_by_duration(
    short_color: str = "Teal",
    medium_color: str = "Blue",
    long_color: str = "Purple",
    short_threshold: float = 5.0,
    long_threshold: float = 30.0,
    track_index: int = 1,
) -> dict[str, str]:
    """Color-tag clips based on their duration (useful for sorting b-roll vs interviews)."""
    bridge = get_bridge()
    items = bridge.get_timeline_items(track_index)

    results: dict[str, str] = {}
    for item in items:
        name = item.GetName()
        duration_str = item.GetDuration() if hasattr(item, "GetDuration") else "0"
        try:
            # Duration comes in frames; assume 24fps if no fps info
            tl = bridge.get_current_timeline()
            fps_str = tl.GetSetting("timelineFrameRate") if tl else "24"
            fps = float(fps_str) if fps_str else 24.0
            frames = float(str(duration_str))
            seconds = frames / fps
        except (ValueError, ZeroDivisionError):
            seconds = 0.0

        if seconds < short_threshold:
            color = short_color
        elif seconds > long_threshold:
            color = long_color
        else:
            color = medium_color

        bridge.set_clip_color(item, color)
        results[name] = color
        logger.info("Tagged %s as %s (%.1fs)", name, color, seconds)

    return results


def add_node_to_all_clips(track_index: int = 1) -> int:
    """Add a new color node to every clip. Returns count of clips modified."""
    bridge = get_bridge()
    items = bridge.get_timeline_items(track_index)
    count = 0
    for item in items:
        if bridge.add_node(item):
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-grade clips in the current timeline")
    sub = parser.add_subparsers(dest="command")

    lut_p = sub.add_parser("apply-lut", help="Apply a LUT to all clips")
    lut_p.add_argument("lut_path", help="Path to .cube, .dctl, or .3dl file")
    lut_p.add_argument("--node", type=int, default=1, help="Node index (default: 1)")
    lut_p.add_argument("--track", type=int, default=1, help="Video track (default: 1)")

    tag_p = sub.add_parser("color-tag", help="Color-tag clips by duration")
    tag_p.add_argument("--short-sec", type=float, default=5.0)
    tag_p.add_argument("--long-sec", type=float, default=30.0)

    sub.add_parser("add-nodes", help="Add a color node to all clips")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    if args.command == "apply-lut":
        results = apply_lut_to_all_clips(args.lut_path, args.node, args.track)
        ok = sum(1 for v in results.values() if v)
        print(f"Applied LUT to {ok}/{len(results)} clips")
    elif args.command == "color-tag":
        results = color_tag_by_duration(
            short_threshold=args.short_sec, long_threshold=args.long_sec
        )
        for name, color in results.items():
            print(f"  {name}: {color}")
    elif args.command == "add-nodes":
        count = add_node_to_all_clips()
        print(f"Added nodes to {count} clips")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
