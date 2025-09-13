import sys
from pathlib import Path
import pytest

# make src modules importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.gw import aggregate_gw


def test_uses_spi_hybrid_when_ai_spi_valid():
    ai_spi = {"ai_spi": 0.0, "positives": 0, "evaluated": 10}
    weights = {"vui": 0.5, "r_spi": 0.5, "r_ci": 0.0}
    bands = {"low": 0.3, "med": 0.7}
    res = aggregate_gw(0.6, 0.2, None, weights, bands, ai_spi=ai_spi, spi_rule=0.4)
    # if spi_rule (0.4) were used, gw would be 0.6
    assert res["gw"] == pytest.approx(0.7)
