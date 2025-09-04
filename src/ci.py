import numpy as np

def normalize_units(value, unit, unit_map):
    return float(value) * unit_map[unit.lower()]

def winsorize(arr, p_low=1, p_high=99):
    lo, hi = np.percentile(arr, [p_low, p_high])
    return np.clip(arr, lo, hi)

def ci_light(series_by_year:dict, winsor=(1,99), restated_flags:dict=None):
    years = sorted(series_by_year)
    vals = np.array([series_by_year[y] for y in years], dtype=float)
    w = winsorize(vals, winsor[0], winsor[1])
    ci = {}
    for i in range(1, len(years)):
        vt, vp = w[i], w[i-1]
        ci[years[i]] = max(0.0, 1.0 - abs(vt - vp) / max(vt, vp))
    return {"ci_by_year": ci, "winsor_bounds": (float(np.min(w)), float(np.max(w))), "restated": restated_flags or {}}
