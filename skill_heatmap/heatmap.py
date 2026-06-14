"""
신호 발생 후 5일 수익률 계산 및 주별 집계
"""

import pandas as pd
import numpy as np
import datetime
from .skills import SKILL_REGISTRY
from .indicators import add_all


def calc_d5_return(df: pd.DataFrame, signal_date: pd.Timestamp) -> float | None:
    dates = df["date"].tolist()
    if signal_date not in dates:
        return None
    idx       = dates.index(signal_date)
    entry_idx = idx + 1
    exit_idx  = idx + 6
    if exit_idx >= len(df):
        return None
    entry = df.iloc[entry_idx]["close"]
    exit_ = df.iloc[exit_idx]["close"]
    return (exit_ - entry) / entry * 100


def get_week_label(date: pd.Timestamp) -> str:
    return f"W{date.isocalendar().week:02d}"


def run_skill_heatmap(
    ohlcv_dict: dict[str, pd.DataFrame],
    year: int = None,
) -> pd.DataFrame:
    if year is None:
        year = datetime.date.today().year

    results = {sk: {} for sk in SKILL_REGISTRY}

    for ticker, raw_df in ohlcv_dict.items():
        if raw_df.empty or len(raw_df) < 60:
            continue
        df = add_all(raw_df)

        for skill_name, skill_fn in SKILL_REGISTRY.items():
            try:
                signals = skill_fn(df)
            except Exception as e:
                print(f"[WARN] {skill_name}/{ticker}: {e}")
                continue

            for sig_date in signals:
                if sig_date.year != year:
                    continue
                ret = calc_d5_return(df, sig_date)
                if ret is None:
                    continue
                week = get_week_label(sig_date)
                results[skill_name].setdefault(week, []).append(ret)

    rows = []
    for skill, week_data in results.items():
        for week, rets in week_data.items():
            n        = len(rets)
            mean_ret = float(np.mean(rets))
            win_rate = float(np.mean([r > 0 for r in rets]) * 100)
            rows.append({"skill": skill, "week": week, "mean": mean_ret, "n": n, "win_rate": win_rate})

    if not rows:
        return pd.DataFrame(columns=["skill","week","mean","n","win_rate"])

    return pd.DataFrame(rows)


def pivot_for_heatmap(df: pd.DataFrame) -> dict:
    out = {}
    for _, row in df.iterrows():
        sk = row["skill"]
        wk = row["week"]
        out.setdefault(sk, {})[wk] = {
            "mean":     round(row["mean"], 1),
            "n":        int(row["n"]),
            "win_rate": round(row["win_rate"]),
        }
    return out
