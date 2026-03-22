"""Tests to verify all DCTL files exist and have valid structure."""

from pathlib import Path

import pytest

DCTL_DIR = Path(__file__).parent.parent / "src" / "dctl"

EXPECTED_DCTLS = [
    "curves/SCurve.dctl",
    "curves/InverseSCurve.dctl",
    "curves/PowerKnee.dctl",
    "limiters/SignalLimiter.dctl",
    "limiters/LumaLimiter.dctl",
    "limiters/Clamp.dctl",
    "analysis/FalseColor.dctl",
    "analysis/GrayChart.dctl",
    "analysis/MidSelect.dctl",
    "conversion/Full2Legal.dctl",
    "conversion/Legal2Full.dctl",
    "conversion/Quantize.dctl",
    "creative/ChannelSaturation.dctl",
    "creative/FilmEmulation.dctl",
    "creative/SkinToneIndicator.dctl",
    "creative/StepRamp.dctl",
    "creative/FilmGrain.dctl",
    "creative/Halation.dctl",
    "creative/TealOrange.dctl",
    "creative/BleachBypass.dctl",
]


@pytest.mark.parametrize("dctl_path", EXPECTED_DCTLS)
def test_dctl_exists(dctl_path):
    full = DCTL_DIR / dctl_path
    assert full.exists(), f"Missing DCTL: {dctl_path}"


@pytest.mark.parametrize("dctl_path", EXPECTED_DCTLS)
def test_dctl_has_transform_function(dctl_path):
    full = DCTL_DIR / dctl_path
    content = full.read_text()
    assert "float3 transform(" in content, f"Missing transform() in {dctl_path}"


@pytest.mark.parametrize("dctl_path", EXPECTED_DCTLS)
def test_dctl_has_device_qualifier(dctl_path):
    full = DCTL_DIR / dctl_path
    content = full.read_text()
    assert "__DEVICE__" in content, f"Missing __DEVICE__ qualifier in {dctl_path}"


def test_all_dctls_counted():
    """Verify the expected count matches what's on disk."""
    actual = list(DCTL_DIR.rglob("*.dctl"))
    assert len(actual) == len(EXPECTED_DCTLS), (
        f"Expected {len(EXPECTED_DCTLS)} DCTLs, found {len(actual)}"
    )
