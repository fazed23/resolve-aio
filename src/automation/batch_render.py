"""
Batch Render — Render multiple timelines or projects in sequence.

Usage:
    python -m src.automation.batch_render --preset "H.264 Master" --output /path/to/output
    python -m src.automation.batch_render --all-timelines --preset "ProRes Master"
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from ..mcp.resolve_bridge import get_bridge

logger = logging.getLogger("resolve_aio.batch_render")


def render_all_timelines(
    preset: str = "H.264 Master",
    output_dir: str = "",
    format_override: str | None = None,
) -> dict[str, bool]:
    """Render every timeline in the current project."""
    bridge = get_bridge()
    if not bridge.connected:
        logger.error("Not connected to Resolve")
        return {}

    proj = bridge.get_current_project()
    if not proj:
        logger.error("No project open")
        return {}

    results: dict[str, bool] = {}
    timelines = bridge.list_timelines()

    for tl_info in timelines:
        name = tl_info["name"]
        logger.info("Setting up render for timeline: %s", name)
        bridge.set_current_timeline(name)

        bridge.set_render_preset(preset)

        settings: dict = {}
        if output_dir:
            settings["TargetDir"] = output_dir
        settings["CustomName"] = name
        if format_override:
            settings["FormatWidth"] = format_override
        if settings:
            bridge.set_render_settings(settings)

        job_id = bridge.add_render_job()
        if not job_id:
            logger.warning("Failed to add render job for %s", name)
            results[name] = False
            continue

        results[name] = True
        logger.info("Added render job for %s (job: %s)", name, job_id)

    # Start all queued jobs
    if any(results.values()):
        logger.info("Starting render of %d timelines...", sum(results.values()))
        bridge.start_render()

        # Wait for completion
        while bridge.get_render_status().get("is_rendering", False):
            time.sleep(2)

        logger.info("Batch render complete")

    return results


def render_specific_timelines(
    timeline_names: list[str],
    preset: str = "H.264 Master",
    output_dir: str = "",
) -> dict[str, bool]:
    """Render only the specified timelines."""
    bridge = get_bridge()
    results: dict[str, bool] = {}

    for name in timeline_names:
        ok = bridge.set_current_timeline(name)
        if not ok:
            logger.warning("Timeline not found: %s", name)
            results[name] = False
            continue

        bridge.set_render_preset(preset)
        if output_dir:
            bridge.set_render_settings({"TargetDir": output_dir, "CustomName": name})

        job_id = bridge.add_render_job()
        results[name] = bool(job_id)

    if any(results.values()):
        bridge.start_render()
        while bridge.get_render_status().get("is_rendering", False):
            time.sleep(2)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch render timelines from DaVinci Resolve")
    parser.add_argument("--preset", default="H.264 Master", help="Render preset name")
    parser.add_argument("--output", default="", help="Output directory")
    parser.add_argument("--all-timelines", action="store_true", help="Render all timelines")
    parser.add_argument("--timelines", nargs="*", help="Specific timeline names to render")
    parser.add_argument("--format", default=None, help="Override format (mp4, mov, mxf)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    if args.all_timelines:
        results = render_all_timelines(args.preset, args.output, args.format)
    elif args.timelines:
        results = render_specific_timelines(args.timelines, args.preset, args.output)
    else:
        print("Specify --all-timelines or --timelines <name1> <name2> ...")
        sys.exit(1)

    for name, ok in results.items():
        status = "OK" if ok else "FAILED"
        print(f"  {name}: {status}")


if __name__ == "__main__":
    main()
