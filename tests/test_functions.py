import sys
from pathlib import Path
import pytest

# make src modules importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / 'src'))

from src.spi import normalize_year_tokens, is_specific
from src.vui import compute_vui
from src.ci import ci_light
from src.gw import aggregate_gw
from src.alerts import delta_warnings


def test_normalize_year_tokens():
    assert normalize_year_tokens('This is 2-0-3-0 event') == 'This is 2030 event'
    assert normalize_year_tokens('Plans for 20 24 are ready') == 'Plans for 2024 are ready'
    assert normalize_year_tokens('Year 2024 already fine') == 'Year 2024 already fine'


def test_is_specific():
    cfg = {
        'spi': {
            'unit_patterns': ['tons'],
            'target_patterns': ['reduce'],
            'baseline_patterns': ['base'],
            'strict_excludes': ['not specific']
        }
    }
    assert is_specific('Reduce emissions by 20 tons from base year', cfg)
    assert not is_specific('Reduce emissions by 20 tons not specific', cfg)
    assert not is_specific('Only numbers like 20 here', cfg)


def test_compute_vui():
    sentences = [
        {'text': 'Maybe we are uncertain.'},
        {'text': 'Surely no maybe, but possibly yes.'}
    ]
    cfg = {
        'vui': {
            'lm_uncertainty': ['maybe'],
            'hedges': ['possibly'],
            'divisor_per_1000': 100
        }
    }
    res = compute_vui(sentences, cfg)
    assert res['vui_hits'] == 3
    assert res['words'] == 10
    assert res['vui_per_1000'] == pytest.approx(300.0)
    assert res['vui_norm'] == pytest.approx(1.0)


def test_ci_light():
    series = {2020: 100, 2021: 110, 2022: 105}
    res = ci_light(series)
    assert res['winsor_bounds'] == pytest.approx((100.1, 109.9))
    assert res['ci_by_year'][2021] == pytest.approx(0.9108280254777069)
    assert res['ci_by_year'][2022] == pytest.approx(0.9554140127388534)
    assert res['restated'] == {}


@pytest.mark.parametrize(
    'vui_norm, spi_hybrid, ci_or_none, expected_gw, expected_band, expected_weights',
    [
        (0.6, 0.2, None, 0.675, 'medium', {'vui': 0.625, 'r_spi': 0.375, 'r_ci': 0.0}),
        (0.6, 0.2, 0.9, 0.56, 'medium', {'vui': 0.5, 'r_spi': 0.3, 'r_ci': 0.2}),
    ]
)
def test_aggregate_gw(vui_norm, spi_hybrid, ci_or_none, expected_gw, expected_band, expected_weights):
    weights = {'vui': 0.5, 'r_spi': 0.3, 'r_ci': 0.2}
    bands = {'low': 0.3, 'med': 0.7}
    res = aggregate_gw(vui_norm, spi_hybrid, ci_or_none, weights, bands)
    assert res['gw'] == pytest.approx(expected_gw)
    assert res['band'] == expected_band
    for k, v in expected_weights.items():
        assert res['effective_weights'][k] == pytest.approx(v)


def test_delta_warnings():
    res = delta_warnings(0.6, 0.3, 0.3, 0.2)
    assert "ΔVUI_norm +0.300 exceeds ±0.2" in res
    assert "ΔSPI +0.100 exceeds ±0.05" in res
    assert delta_warnings(0.35, 0.21, 0.3, 0.18) == []
