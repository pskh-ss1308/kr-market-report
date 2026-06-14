"""
스킬별 매수 신호 로직 v2 — 조건 완화 버전
"""

import pandas as pd
import numpy as np
from .indicators import add_all
from collections import Counter


def _prep(df):
    if "ma20" not in df.columns:
        df = add_all(df)
    return df

def _has_min_bars(df, n=60):
    return len(df) >= n


def vcp(df):
    if not _has_min_bars(df, 60):
        return []
    df = _prep(df)
    signals = []
    for i in range(40, len(df)):
        row    = df.iloc[i]
        row_40 = df.iloc[i - 40]
        if pd.isna(row["ma20"]) or pd.isna(row["atr_ratio"]):
            continue
        cond1 = row["pct_from_52w_high"] >= -25
        cond2 = row["atr_ratio"] < row_40["atr_ratio"] * 0.8
        cond3 = row["vol_ratio20"] < 1.2
        cond4 = row["close"] > row["ma20"]
        if cond1 and cond2 and cond3 and cond4:
            signals.append(row["date"])
    return signals


def sector_rotation(df):
    if not _has_min_bars(df, 60):
        return []
    df = _prep(df)
    signals = []
    for i in range(40, len(df)):
        row = df.iloc[i]
        if pd.isna(row["mom20"]):
            continue
        cond1 = row["mom20"] > 3
        cond2 = row["vol_ratio20"] > 1.0
        cond3 = row["close"] > row["ma20"]
        if cond1 and cond2 and cond3:
            signals.append(row["date"])
    return signals


def flow_momentum(df):
    if not _has_min_bars(df, 30):
        return []
    df = _prep(df)
    signals = []
    for i in range(20, len(df)):
        row  = df.iloc[i]
        prev = df.iloc[i - 1]
        if pd.isna(row["rsi14"]):
            continue
        cond1 = row["vol_ratio20"] > 1.8
        cond2 = row["close"] > prev["close"]
        cond3 = row["close"] > row["ma20"]
        cond4 = 35 <= row["rsi14"] <= 75
        if cond1 and cond2 and cond3 and cond4:
            signals.append(row["date"])
    return signals


def pre_surge(df):
    if not _has_min_bars(df, 60):
        return []
    df = _prep(df)
    signals = []
    for i in range(40, len(df)):
        row    = df.iloc[i]
        window = df["bb_width"].iloc[i-40:i]
        if pd.isna(row["bb_width"]) or pd.isna(row["rsi14"]):
            continue
        bb_pct = (row["bb_width"] - window.min()) / (window.max() - window.min() + 1e-9)
        cond1 = bb_pct < 0.25
        cond2 = row["vol_ratio5"] < 0.9
        cond3 = row["close"] > row["bb_mid"]
        cond4 = 40 <= row["rsi14"] <= 65
        if cond1 and cond2 and cond3 and cond4:
            signals.append(row["date"])
    return signals


def contrarian_reversal(df):
    if not _has_min_bars(df, 30):
        return []
    df = _prep(df)
    signals = []
    for i in range(20, len(df)):
        row  = df.iloc[i]
        prev = df.iloc[i - 1]
        if pd.isna(row["rsi14"]):
            continue
        cond1 = row["rsi14"] < 35
        cond2 = row["close"] > row["open"]
        cond3 = row["close"] > prev["low"]
        if cond1 and cond2 and cond3:
            signals.append(row["date"])
    return signals


def narrative_momentum(df):
    if not _has_min_bars(df, 60):
        return []
    df = _prep(df)
    signals = []
    for i in range(40, len(df)):
        row = df.iloc[i]
        if pd.isna(row["mom20"]):
            continue
        cond1 = row["pct_from_52w_high"] >= -20
        cond2 = row["mom20"] > 5
        cond3 = row["vol_ratio20"] > 1.2
        cond4 = row["ma5"] > row["ma20"]
        if cond1 and cond2 and cond3 and cond4:
            signals.append(row["date"])
    return signals


def value_chain(df):
    if not _has_min_bars(df, 60):
        return []
    df = _prep(df)
    signals = []
    for i in range(40, len(df)):
        row       = df.iloc[i]
        ma20_prev = df["ma20"].iloc[i - 5]
        if pd.isna(row["mom20"]) or pd.isna(row["rsi14"]):
            continue
        cond1 = row["mom20"] > 3
        cond2 = row["ma20"] > ma20_prev
        cond3 = row["vol_ratio20"] > 0.8
        cond4 = 45 <= row["rsi14"] <= 70
        if cond1 and cond2 and cond3 and cond4:
            signals.append(row["date"])
    return signals


def best_of_best(df):
    skill_funcs = [vcp, sector_rotation, flow_momentum, pre_surge, narrative_momentum]
    all_signals = []
    for fn in skill_funcs:
        all_signals.extend(fn(df))
    counts = Counter(all_signals)
    return [date for date, cnt in counts.items() if cnt >= 2]


SKILL_REGISTRY = {
    "vcp":                 vcp,
    "sector_rotation":     sector_rotation,
    "flow_momentum":       flow_momentum,
    "pre_surge":           pre_surge,
    "contrarian_reversal": contrarian_reversal,
    "narrative_momentum":  narrative_momentum,
    "value_chain":         value_chain,
    "best_of_best":        best_of_best,
}
