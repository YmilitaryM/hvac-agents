"""Automatic fault diagnostics for HVAC equipment.

Each detector returns a dict with:
    {detected: bool, confidence: float (0-1), message: str}
"""

import math


def detect_surge(
    plr: float,
    surge_boundary: float,
    duration_exceeded: bool,
) -> dict:
    """Detect compressor surge.

    A chiller is surging when its PLR falls below the surge boundary.
    *duration_exceeded* indicates whether the condition has persisted beyond
    a configurable grace period (e.g. 5 minutes).

    Args:
        plr: Current part-load ratio (0-1).
        surge_boundary: Minimum safe PLR for current condenser conditions.
        duration_exceeded: True if PLR has been below boundary for too long.

    Returns:
        Detection result dict.
    """
    below_boundary = plr < surge_boundary

    if not below_boundary:
        return {
            "detected": False,
            "confidence": 1.0,
            "message": "Chiller operating above surge boundary.",
        }

    if duration_exceeded:
        margin = surge_boundary - plr
        confidence = min(1.0, 0.5 + margin * 2.0)
        return {
            "detected": True,
            "confidence": round(confidence, 2),
            "message": (
                f"Surge detected — PLR {plr:.3f} below boundary "
                f"{surge_boundary:.3f} for extended period (margin {margin:.3f})."
            ),
        }

    return {
        "detected": True,
        "confidence": 0.4,
        "message": (
            f"Possible surge — PLR {plr:.3f} below boundary "
            f"{surge_boundary:.3f} but duration not yet exceeded."
        ),
    }


def detect_fouling(
    cop: float,
    design_cop: float,
    trend_data: list[float],
) -> dict:
    """Detect heat-exchanger fouling from COP degradation trend.

    Args:
        cop: Current COP.
        design_cop: Design (clean) COP under the same conditions.
        trend_data: Recent COP readings (oldest first). At least 5 points
                    are needed for a reliable trend.

    Returns:
        Detection result dict.
    """
    c_floor = 0.001
    if design_cop < c_floor:
        return {
            "detected": False,
            "confidence": 0.0,
            "message": "Invalid design COP — cannot assess fouling.",
        }

    ratio = cop / design_cop

    # Need enough history to establish a trend
    if len(trend_data) < 5:
        if ratio < 0.85:
            return {
                "detected": True,
                "confidence": round(min(0.6, (1.0 - ratio) * 2.0), 2),
                "message": (
                    f"COP ratio {ratio:.2f} suggests fouling, "
                    f"but insufficient trend data for confirmation."
                ),
            }
        return {
            "detected": False,
            "confidence": 0.3,
            "message": "Insufficient trend data to evaluate fouling.",
        }

    # Simple linear trend on the COP ratio
    n = len(trend_data)
    # Normalize trend data by design COP so we track ratio
    ratios = [v / design_cop if design_cop > c_floor else 1.0 for v in trend_data]
    mean_x = (n - 1) / 2.0
    mean_y = sum(ratios) / n
    num = sum((i - mean_x) * (ratios[i] - mean_y) for i in range(n))
    den = sum((i - mean_x) ** 2 for i in range(n))
    slope = num / den if den > 0 else 0.0

    # Degrading trend + current ratio low → confident fouling call
    degrading = slope < -0.001
    ratio_low = ratio < 0.85

    if degrading and ratio_low:
        return {
            "detected": True,
            "confidence": round(min(1.0, 0.6 + abs(slope) * 100.0), 2),
            "message": (
                f"Fouling detected — COP ratio {ratio:.2f} with degrading trend "
                f"(slope {slope:.4f}/step)."
            ),
        }

    if degrading:
        return {
            "detected": True,
            "confidence": round(min(0.8, 0.4 + abs(slope) * 80.0), 2),
            "message": (
                f"Early fouling indicator — COP ratio {ratio:.2f} with degrading trend "
                f"(slope {slope:.4f}/step)."
            ),
        }

    if ratio_low:
        return {
            "detected": True,
            "confidence": round(min(0.7, (1.0 - ratio) * 3.0), 2),
            "message": f"Low COP ratio {ratio:.2f} but no clear degrading trend.",
        }

    return {
        "detected": False,
        "confidence": round(max(0.0, min(1.0, ratio)), 2),
        "message": f"COP ratio {ratio:.2f} — no fouling detected.",
    }


def detect_sensor_drift(
    readings: list[float],
    expected_range: tuple[float, float],
    window: int = 168,
) -> dict:
    """Detect sensor drift by checking whether recent readings have wandered
    outside the expected range over a rolling window.

    Args:
        readings: Time-series readings from the sensor (oldest first).
        expected_range: (low, high) — the acceptable value range.
        window: Number of most recent readings to examine (default 168, i.e.
                one week of hourly data).

    Returns:
        Detection result dict.
    """
    if len(readings) < 2:
        return {
            "detected": False,
            "confidence": 0.0,
            "message": "Insufficient readings for drift detection.",
        }

    low, high = expected_range
    if low >= high:
        return {
            "detected": False,
            "confidence": 0.0,
            "message": "Invalid expected range for drift detection.",
        }

    # Focus on the most recent window
    recent = readings[-window:] if len(readings) >= window else readings

    outliers = [v for v in recent if v < low or v > high]
    outlier_frac = len(outliers) / len(recent) if recent else 0.0

    # Compute drift magnitude as slope of linear regression over recent window
    n = len(recent)
    mean_x = (n - 1) / 2.0
    mean_y = sum(recent) / n
    num = sum((i - mean_x) * (recent[i] - mean_y) for i in range(n))
    den = sum((i - mean_x) ** 2 for i in range(n))
    slope = num / den if den > 0 else 0.0

    # Normalize slope by the expected range width
    range_width = high - low
    norm_slope = abs(slope) / range_width if range_width > 0 else 0.0

    # Detection logic
    if outlier_frac > 0.5:
        # Majority of recent readings are out of range — probable failure
        return {
            "detected": True,
            "confidence": round(min(1.0, 0.7 + outlier_frac * 0.3), 2),
            "message": (
                f"Sensor failure suspected — {outlier_frac:.0%} of recent readings "
                f"outside [{low}, {high}]."
            ),
        }

    if norm_slope > 0.001:
        # Drifting but still within range for now
        direction = "upward" if slope > 0 else "downward"
        confidence = round(min(0.9, 0.3 + norm_slope * 50.0), 2)
        return {
            "detected": True,
            "confidence": confidence,
            "message": (
                f"Sensor drift detected ({direction}, normalized rate {norm_slope:.5f}/step) "
                f"— {outlier_frac:.0%} outliers in recent window."
            ),
        }

    if outlier_frac > 0.1:
        return {
            "detected": True,
            "confidence": round(min(0.7, 0.3 + outlier_frac * 2.0), 2),
            "message": (
                f"Sensor showing intermittent outliers ({outlier_frac:.0%}) "
                f"but no sustained drift."
            ),
        }

    return {
        "detected": False,
        "confidence": round(max(0.0, 1.0 - outlier_frac), 2),
        "message": f"Sensor readings within expected range [{low}, {high}].",
    }
