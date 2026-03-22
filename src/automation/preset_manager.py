"""
Preset Manager — Install, list, and manage DCTL/LUT/PowerGrade presets.

Handles copying files to the correct Resolve directories and managing
the ResolveAIO preset library.
"""

from __future__ import annotations

import argparse
import logging
import os
import platform
import re
import shutil
from pathlib import Path

logger = logging.getLogger("resolve_aio.preset_manager")

# Resolve LUT directories by platform
LUT_DIRS = {
    "Darwin": "/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT",
    "Windows": os.path.join(
        os.environ.get("PROGRAMDATA", r"C:\ProgramData"),
        "Blackmagic Design", "DaVinci Resolve", "Support", "LUT",
    ),
    "Linux": "/opt/resolve/LUT",
}

# File type to subdirectory mapping
TYPE_MAP = {
    ".dctl": "DCTL",
    ".cube": "LUT",
    ".3dl": "LUT",
    ".look": "PowerGrade",
    ".drx": "PowerGrade",
    ".setting": "FusionTemplate",
}

TEMPLATE_DIRS = {
    "Darwin": Path.home() / "Library" / "Application Support" / "Blackmagic Design" / "DaVinci Resolve" / "Fusion" / "Templates" / "Edit",
    "Windows": Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Fusion" / "Templates" / "Edit",
    "Linux": Path.home() / ".local" / "share" / "DaVinciResolve" / "Fusion" / "Templates" / "Edit",
}

METADATA: dict[str, dict[str, str]] = {
    "Kodak2383Print.cube": {
        "name": "Kodak 2383 Print",
        "description": "Warm print-film LUT with gentle density and restrained blues.",
    },
    "Fuji3513Print.cube": {
        "name": "Fuji 3513 Print",
        "description": "Cooler print-stock LUT with cyan bias and softer reds.",
    },
    "AgfaVista400.cube": {
        "name": "Agfa Vista 400",
        "description": "Consumer negative-film LUT with brighter greens and crisp mids.",
    },
    "FadedPortra.cube": {
        "name": "Faded Portra",
        "description": "Matte portrait LUT with lifted blacks and warm skin bias.",
    },
    "BleachBypass.cube": {
        "name": "Bleach Bypass",
        "description": "High-contrast, low-saturation LUT inspired by silver-retention processing.",
    },
    "CrossProcess.cube": {
        "name": "Cross Process",
        "description": "Color-shifted LUT with pushed blues and punchy greens.",
    },
    "FadeInUp.setting": {
        "name": "Fade In Up",
        "description": "Title rises into place while fading on.",
    },
    "LowerThirdClean.setting": {
        "name": "Lower Third Clean",
        "description": "Minimal lower third with editable name and role text.",
    },
    "TypewriterText.setting": {
        "name": "Typewriter",
        "description": "Character-by-character reveal for hooks, captions, and openers.",
    },
    "SlideInLeft.setting": {
        "name": "Slide In Left",
        "description": "Title slides from the left edge into a centered position.",
    },
    "BounceIn.setting": {
        "name": "Bounce In",
        "description": "Elastic text entrance with a quick overshoot.",
    },
    "ScalePop.setting": {
        "name": "Scale Pop",
        "description": "Fast scale-up title for social cuts and punchy callouts.",
    },
    "SubtitleBanner.setting": {
        "name": "Subtitle Banner",
        "description": "Centered subtitle banner with a semi-transparent backing plate.",
    },
    "HookCenter.setting": {
        "name": "Hook Center",
        "description": "Vertical-video hook title with bold center framing.",
    },
    "ScrollCredits.setting": {
        "name": "Scroll Credits",
        "description": "Long-form rolling credits template for edit or delivery slates.",
    },
    "BoxReveal.setting": {
        "name": "Box Reveal",
        "description": "Bold center title on a translucent plate that lifts into frame.",
    },
    "PunchIn.setting": {
        "name": "Punch In",
        "description": "Fast scale-in headline for hooks, trailers, and promos.",
    },
    "CornerLabel.setting": {
        "name": "Corner Label",
        "description": "Top-corner label with a compact color block for tags and sections.",
    },
    "StompStack.setting": {
        "name": "Stomp Stack",
        "description": "Two-line stacked title with an eyebrow and a heavy main line.",
    },
    "UnderlineRise.setting": {
        "name": "Underline Rise",
        "description": "Centered title with a clean underline accent and upward motion.",
    },
    "CaptionPop.setting": {
        "name": "Caption Pop",
        "description": "Bottom caption plate that scales in for reels and talk-to-camera clips.",
    },
    "PromoSlug.setting": {
        "name": "Promo Slug",
        "description": "Wide side-mounted promo card with title and supporting subtitle.",
    },
    "FocusFrame.setting": {
        "name": "Focus Frame",
        "description": "Minimal center title framed by animated guide lines.",
    },
    "SplitTitle.setting": {
        "name": "Split Title",
        "description": "Balanced split-screen style title with divider and subtitle lane.",
    },
    "NoteCallout.setting": {
        "name": "Note Callout",
        "description": "Labeled callout box for tips, warnings, or chapter markers.",
    },
    "MonoTicker.setting": {
        "name": "Mono Ticker",
        "description": "Monospaced ticker-style banner for news hits and technical overlays.",
    },
    "DipToColor.setting": {
        "name": "Dip To Color",
        "description": "Stylized dip transition with an editable color wash.",
    },
    "WhipSlide.setting": {
        "name": "Whip Slide",
        "description": "Directional push transition for fast-paced edits and reels.",
    },
    "FlashFrame.setting": {
        "name": "Flash Frame",
        "description": "Hard flash transition with a brief white burst between shots.",
    },
    "ZoomBlur.setting": {
        "name": "Zoom Blur",
        "description": "Punchy zoom-style transition for trailers and social promos.",
    },
    "SplitWipe.setting": {
        "name": "Split Wipe",
        "description": "Center split wipe with mirrored movement from both edges.",
    },
    "SoftLightLeak.setting": {
        "name": "Soft Light Leak",
        "description": "Warm light leak transition for lifestyle edits and mood reels.",
    },
}


def get_lut_dir() -> Path:
    """Get the Resolve LUT directory for the current platform."""
    system = platform.system()
    path = LUT_DIRS.get(system)
    if not path:
        raise RuntimeError(f"Unsupported platform: {system}")
    return Path(path)


def get_fusion_template_dir(category: str = "Titles") -> Path:
    """Get the Resolve Fusion template directory for the current platform."""
    system = platform.system()
    base = TEMPLATE_DIRS.get(system)
    if not base:
        raise RuntimeError(f"Unsupported platform: {system}")
    return base / category


def get_bundled_presets_dir() -> Path:
    """Get the path to ResolveAIO's bundled presets."""
    return Path(__file__).parent.parent.parent / "presets"


def _humanize_name(value: str) -> str:
    stem = Path(value).stem.replace("_", " ").replace("-", " ")
    return re.sub(r"(?<!^)(?=[A-Z0-9])", " ", stem).strip()


def _default_description(asset_type: str, category: str, name: str) -> str:
    if asset_type == "DCTL":
        return f"{category} DCTL for {name.lower()} inside the Resolve color pipeline."
    if asset_type == "LUT":
        return f"{category} LUT for quick look development and timeline-wide application."
    if asset_type == "FusionTemplate":
        return f"{category} Fusion template ready to install into the Edit page."
    return f"{asset_type} asset for ResolveAIO."


def _build_asset_entry(path: Path, asset_type: str, category: str, relative: str) -> dict[str, str]:
    meta = METADATA.get(path.name, {})
    name = meta.get("name", _humanize_name(path.name))
    description = meta.get("description", _default_description(asset_type, category, name))
    action = "install" if asset_type == "FusionTemplate" else "apply"
    return {
        "name": name,
        "file_name": path.name,
        "type": asset_type,
        "category": category,
        "description": description,
        "path": str(path),
        "relative": relative.replace(os.sep, "/"),
        "action": action,
    }


def list_bundled_assets(asset_type: str | None = None) -> list[dict[str, str]]:
    """List real bundled ResolveAIO assets that ship with the project."""
    assets: list[dict[str, str]] = []
    dctl_dir = Path(__file__).parent.parent / "dctl"
    presets_dir = get_bundled_presets_dir()

    for file_path in dctl_dir.rglob("*.dctl"):
        entry = _build_asset_entry(
            file_path,
            "DCTL",
            file_path.parent.name,
            str(Path("dctl") / file_path.parent.name / file_path.name),
        )
        if asset_type and entry["type"].lower() != asset_type.lower():
            continue
        assets.append(entry)

    for file_path in presets_dir.rglob("*"):
        if not file_path.is_file():
            continue
        ext = file_path.suffix.lower()
        asset_kind = TYPE_MAP.get(ext)
        if asset_kind not in {"LUT", "PowerGrade", "FusionTemplate"}:
            continue
        relative = str(file_path.relative_to(presets_dir))
        entry = _build_asset_entry(file_path, asset_kind, file_path.parent.name, relative)
        if asset_type and entry["type"].lower() != asset_type.lower():
            continue
        assets.append(entry)

    assets.sort(key=lambda item: (item["type"], item["category"], item["name"]))
    return assets


def find_bundled_asset(name: str, asset_type: str | None = None) -> dict[str, str] | None:
    """Resolve a bundled asset by display name, filename, stem, or relative path."""
    needle = name.strip().lower()
    for asset in list_bundled_assets(asset_type=asset_type):
        candidates = {
            asset["name"].lower(),
            asset["file_name"].lower(),
            Path(asset["file_name"]).stem.lower(),
            asset["relative"].lower(),
        }
        if needle in candidates:
            return asset
    return None


def list_installed_presets(preset_type: str | None = None) -> list[dict[str, str]]:
    presets = []
    lut_dir = get_lut_dir()

    if lut_dir.exists():
        for root, _, files in os.walk(lut_dir):
            for f in files:
                ext = Path(f).suffix.lower()
                if ext == ".setting":
                    continue
                if ext in TYPE_MAP:
                    ptype = TYPE_MAP[ext]
                    if preset_type and ptype.lower() != preset_type.lower():
                        continue
                    presets.append({
                        "name": f,
                        "type": ptype,
                        "path": str(Path(root) / f),
                        "relative": str(Path(root).relative_to(lut_dir) / f),
                    })
    else:
        logger.warning("LUT directory does not exist: %s", lut_dir)

    try:
        template_root = get_fusion_template_dir().parent
    except RuntimeError:
        template_root = None

    if template_root and template_root.exists():
        for template in template_root.rglob("*.setting"):
            if preset_type and "fusiontemplate" != preset_type.lower():
                continue
            presets.append({
                "name": template.name,
                "type": "FusionTemplate",
                "path": str(template),
                "relative": str(template.relative_to(template_root)),
            })

    return presets


def install_preset(source: str, category: str = "") -> str:
    """Install a preset file to the Resolve LUT directory."""
    src = Path(source)
    if not src.exists():
        raise FileNotFoundError(f"Source file not found: {source}")

    ext = src.suffix.lower()
    ptype = TYPE_MAP.get(ext)
    if not ptype:
        raise ValueError(f"Unknown preset type: {ext}. Supported: {list(TYPE_MAP.keys())}")

    if ptype == "PowerGrade":
        raise ValueError(
            "PowerGrade .drx files are not installed through the LUT directory. "
            "Use src.automation.powergrade_tools to import or apply them through Resolve."
        )
    if ptype == "FusionTemplate":
        target_dir = get_fusion_template_dir(category or src.parent.name)
    else:
        lut_dir = get_lut_dir()
        target_dir = lut_dir / "ResolveAIO"
        if category:
            target_dir = target_dir / category
    target_dir.mkdir(parents=True, exist_ok=True)

    dest = target_dir / src.name
    shutil.copy2(str(src), str(dest))
    logger.info("Installed %s → %s", src.name, dest)
    return str(dest)


def install_bundled_assets(asset_type: str | None = None) -> dict[str, int]:
    """Install bundled ResolveAIO assets and return counts by type."""
    counts: dict[str, int] = {}
    for asset in list_bundled_assets(asset_type=asset_type):
        if asset["type"] == "PowerGrade":
            logger.info(
                "Skipping %s during install; PowerGrades are applied or imported through Resolve, not copied into LUT folders.",
                asset["file_name"],
            )
            continue
        category = asset["category"]
        try:
            install_preset(asset["path"], category=category)
        except Exception as exc:
            logger.error("Failed to install %s: %s", asset["file_name"], exc)
            continue
        counts[asset["type"]] = counts.get(asset["type"], 0) + 1
    return counts


def install_bundled_dctls() -> int:
    """Install all bundled DCTL files from the ResolveAIO library."""
    counts = install_bundled_assets(asset_type="DCTL")
    count = counts.get("DCTL", 0)
    logger.info("Installed %d DCTL files", count)
    return count


def uninstall_preset(name: str) -> bool:
    """Remove an installed preset by filename."""
    lut_dir = get_lut_dir()
    aio_dir = lut_dir / "ResolveAIO"

    for f in aio_dir.rglob(name):
        f.unlink()
        logger.info("Removed %s", f)
        return True

    logger.warning("Preset not found: %s", name)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage ResolveAIO presets")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="List installed presets")
    sub.add_parser("list-bundled", help="List bundled assets that ship with ResolveAIO")
    inst = sub.add_parser("install", help="Install a preset file")
    inst.add_argument("file", help="Path to the preset file")
    inst.add_argument("--category", default="", help="Category subdirectory")

    sub.add_parser("install-bundled", help="Install bundled LUTs, DCTLs, and Fusion templates")

    rm = sub.add_parser("uninstall", help="Remove an installed preset")
    rm.add_argument("name", help="Filename to remove")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    if args.command == "list":
        presets = list_installed_presets()
        for p in presets:
            print(f"  [{p['type']}] {p['name']} — {p['relative']}")
        print(f"\nTotal: {len(presets)} presets")
    elif args.command == "list-bundled":
        assets = list_bundled_assets()
        for asset in assets:
            print(f"  [{asset['type']}] {asset['name']} — {asset['relative']}")
        print(f"\nTotal: {len(assets)} bundled assets")
    elif args.command == "install":
        dest = install_preset(args.file, args.category)
        print(f"Installed to: {dest}")
    elif args.command == "install-bundled":
        counts = install_bundled_assets()
        total = sum(counts.values())
        if counts:
            summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
            print(f"Installed {total} bundled assets ({summary})")
        else:
            print("Installed 0 bundled assets")
    elif args.command == "uninstall":
        ok = uninstall_preset(args.name)
        print("Removed" if ok else "Not found")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
