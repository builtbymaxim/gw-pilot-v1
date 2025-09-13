"""Utility for detecting significant metric changes."""
from typing import List, Optional


def delta_warnings(cur_vui: float, cur_spi: float,
                   prev_vui: Optional[float], prev_spi: Optional[float]) -> List[str]:
    """Return warning messages when year-over-year deltas exceed thresholds."""
    warnings: List[str] = []
    if prev_vui is not None:
        dvui = cur_vui - prev_vui
        if abs(dvui) > 0.2:
            warnings.append(f"ΔVUI_norm {dvui:+.3f} exceeds ±0.2")
    if prev_spi is not None:
        dspi = cur_spi - prev_spi
        if abs(dspi) > 0.05:
            warnings.append(f"ΔSPI {dspi:+.3f} exceeds ±0.05")
    return warnings
