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
        # Fix #9: guard against division by zero when both values are 0
        if vt == 0 and vp == 0:
            ci[years[i]] = 1.0
            continue
        # Fix #3: only penalize emission *increases* (vt > vp).
        # Reductions (vt < vp) yield CI = 1.0 (fully consistent / good).
        change = max(0.0, vt - vp) / max(abs(vt), abs(vp), 1e-9)
        ci[years[i]] = max(0.0, 1.0 - change)
    return {"ci_by_year": ci, "winsor_bounds": (float(np.min(w)), float(np.max(w))), "restated": restated_flags or {}}
