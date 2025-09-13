def aggregate_gw(vui_norm, spi_hybrid, ci_or_none, weights, bands, *, ai_spi=None, spi_rule=None):
    spi_used = spi_hybrid if ai_spi and ai_spi.get("evaluated", 0) > 0 else (spi_rule if spi_rule is not None else spi_hybrid)
    r_spi = 1.0 - spi_used
    if ci_or_none is None:
        wsum = weights["vui"] + weights["r_spi"]
        vw, sw = weights["vui"]/wsum, weights["r_spi"]/wsum
        gw = vw*vui_norm + sw*r_spi
        eff = {"vui": vw, "r_spi": sw, "r_ci": 0.0}
    else:
        r_ci = 1.0 - ci_or_none
        gw = weights["vui"]*vui_norm + weights["r_spi"]*r_spi + weights["r_ci"]*r_ci
        eff = dict(weights)
    band = "low" if gw <= bands["low"] else ("medium" if gw <= bands["med"] else "high")
    return {"gw": float(gw), "band": band, "effective_weights": eff}
