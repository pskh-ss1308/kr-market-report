from __future__ import annotations
import pandas as pd

def compute_correlations(closes, lookback=60):
    if not closes:
        return {"matrix": {}, "lookback": lookback, "window_used": 0}
    df = pd.DataFrame({k: v for k, v in closes.items()}).sort_index()
    returns = df.pct_change(fill_method=None).dropna(how="all").tail(lookback)
    bases  = [b for b in ("KOSPI", "KOSDAQ") if b in returns.columns]
    others = [c for c in returns.columns if c not in ("KOSPI", "KOSDAQ")]
    matrix = {}
    for base in bases:
        row = {}
        for other in others:
            pair = returns[[base, other]].dropna()
            if len(pair) >= 5:
                row[other] = round(float(pair[base].corr(pair[other])), 2)
        matrix[base] = row
    if "KOSPI" in returns and "KOSDAQ" in returns:
        pair = returns[["KOSPI", "KOSDAQ"]].dropna()
        if len(pair) >= 5:
            matrix.setdefault("KOSPI", {})["KOSDAQ"] = round(
                float(pair["KOSPI"].corr(pair["KOSDAQ"])), 2)
    return {"matrix": matrix, "lookback": lookback,
            "window_used": int(len(returns)),
            "note": "일간 수익률 기준 피어슨 상관계수. +1 동행, -1 역행."}
