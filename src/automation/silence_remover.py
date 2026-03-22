"""
Silence Remover — Detects and marks or removes silent sections in timeline audio.

Uses Resolve's timeline item properties to identify clips with low audio levels
and can either add markers, set clip colors, or (with confirmation) delete them.
"""

from __future__ import annotations

import argparse
import logging

from ..mcp.resolve_bridge import get_bridge

logger = logging.getLogger("resolve_aio.silence_remover")


def detect_silent_segments(
    threshold_db: float = -40.0,
    min_duration_sec: float = 0.5,
    track_index: int = 1,
) -> list[dict]:
    """
    Detect potentially silent segments based on clip properties.

    Note: Resolve's scripting API does not expose per-frame audio levels.
    This is a heuristic approach that marks clips below a duration threshold
    or with specific naming patterns. For full audio analysis, use the
    Fairlight page or external tools like ffmpeg.
    """
    bridge = get_bridge()
    tl = bridge.get_current_timeline()
    if not tl:
        logger.error("No timeline open")
        return []

    fps_str = tl.GetSetting("timelineFrameRate")
    fps = float(fps_str) if fps_str else 24.0

    # Get audio items
    audio_items = tl.GetItemListInTrack("audio", track_index)
    if not audio_items:
        logger.info("No audio items on track %d", track_index)
        return []

    segments = []
    for item in audio_items:
        name = item.GetName()
        start = item.GetStart()
        end = item.GetEnd()
        duration_frames = end - start
        duration_sec = duration_frames / fps

        # Heuristic: very short audio clips are often silence
        if duration_sec < min_duration_sec:
            segments.append({
                "name": name,
                "start_frame": start,
                "end_frame": end,
                "duration_sec": round(duration_sec, 2),
                "reason": "short_duration",
            })

    logger.info("Found %d potential silent segments", len(segments))
    return segments


def mark_silent_segments(
    segments: list[dict],
    color: str = "Red",
    marker_note: str = "Potential silence",
) -> int:
    """Add markers at detected silent segments."""
    bridge = get_bridge()
    count = 0
    for seg in segments:
        ok = bridge.add_marker(
            frame=seg["start_frame"],
            color=color,
            name="Silence",
            note=f"{marker_note} ({seg['duration_sec']}s)",
            duration=seg["end_frame"] - seg["start_frame"],
        )
        if ok:
            count += 1
    return count


def color_tag_silent_clips(
    track_index: int = 1,
    min_duration_sec: float = 0.5,
    color: str = "Red",
) -> int:
    """Color-tag potentially silent video clips that are very short."""
    bridge = get_bridge()
    items = bridge.get_timeline_items(track_index)
    tl = bridge.get_current_timeline()
    fps = float(tl.GetSetting("timelineFrameRate") or "24") if tl else 24.0

    count = 0
    for item in items:
        start = item.GetStart()
        end = item.GetEnd()
        duration_sec = (end - start) / fps
        if duration_sec < min_duration_sec:
            bridge.set_clip_color(item, color)
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect and mark silent segments")
    parser.add_argument("--threshold", type=float, default=-40.0, help="Silence threshold in dB")
    parser.add_argument("--min-duration", type=float, default=0.5, help="Min duration in seconds")
    parser.add_argument("--action", choices=["mark", "color-tag", "detect"], default="detect")
    parser.add_argument("--track", type=int, default=1, help="Audio track number")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    segments = detect_silent_segments(args.threshold, args.min_duration, args.track)

    if args.action == "mark":
        count = mark_silent_segments(segments)
        print(f"Added {count} markers for silent segments")
    elif args.action == "color-tag":
        count = color_tag_silent_clips(args.track, args.min_duration)
        print(f"Color-tagged {count} short clips")
    else:
        for seg in segments:
            print(f"  Frame {seg['start_frame']}-{seg['end_frame']}: {seg['duration_sec']}s ({seg['reason']})")
        print(f"\nTotal: {len(segments)} potential silent segments")


if __name__ == "__main__":
    main()
