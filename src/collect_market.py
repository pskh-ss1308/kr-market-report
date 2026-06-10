from __future__ import annotations
import datetime as dt
import pandas as pd
import FinanceDataReader as fdr

SERIES = [
    {"label": "KOSPI",       "symbols": ["KS11"],           "source": "KRX",           "headline": True},
    {"label": "KOSDAQ",      "symbols": ["KQ11"],            "source": "KRX",           "headline": True},
    {"label": "KOSPI200",    "symbols": ["KS200"],           "source": "KRX",           "headline": False},
    {"label": "S&P500",      "symbols": ["US500"],           "source": "Yahoo Finance", "headline": True},
    {"label": "NASDAQ",      "symbols": ["IXIC"],            "source": "Yahoo Finance", "headline": True},
    {"label": "DOW",         "symbols": ["DJI"],             "source": "Yahoo Finance", "headline": False},
    {"label": "SOX(SOXX)",   "symbols": ["SOXX", "SMH"],    "source": "Yahoo Finance", "headline": True},
    {"label": "VIX",         "symbols": ["VIX"],             "source": "Yahoo Finance", "headline": False},
    {"label": "USD/KRW",     "symbols": ["USD/KRW"],         "source": "FDR FX",        "headline": True},
    {"label": "US10Y",       "symbols": ["FRED:DGS10"],      "source": "FRED",          "headline": False},
    {"label": "DollarIndex", "symbols": ["FRED:DTWEXBGS"],   "source": "FRED",          "headline": False},
    {"label": "WTI",         "symbols": ["FRED:DCOILWTICO"], "source": "FRED",          "headline": False},
]

def _pct(cur, prev):
    if not prev or cur is None:
        return None
    return round((cur - prev) / prev * 100, 2)

def _safe_close(df):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return None
    if "Close" in df.columns:
        s = df["Close"].dropna()
        return s if len(s) else None
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            s = df[col].dropna()
            if len(s):
                return s
    return None

def _read_first(symbols, start):
    for sym in symbols:
        try:
            df = fdr.DataReader(sym, start)
            s = _safe_close(df)
            if s is not None and len(s):
                return s, sym
        except Exception as e:
            print(f"[collect_market] {sym} 실패: {type(e).__name__}: {str(e)[:60]}")
    return None, None

def collect_market(lookback_days=180):
    start = (dt.date.today() - dt.timedelta(days=lookback_days)).isoformat()
    closes = {}
    headline, supplementary = [], []
    for spec in SERIES:
        s, used = _read_first(spec["symbols"], start)
        if s is None:
            print(f"[collect_market] {spec['label']} 수집 불가 → 건너뜀")
            continue
        closes[spec["label"]] = s
        cur  = float(s.iloc[-1])
        prev = float(s.iloc[-2]) if len(s) >= 2 else None
        row  = {
            "label": spec["label"], "close": round(cur, 4),
            "prev": round(prev, 4) if prev is not None else None,
            "change_pct": _pct(cur, prev),
            "date": s.index[-1].date().isoformat(),
            "source": spec["source"], "symbol_used": used,
        }
        (headline if spec["headline"] else supplementary).append(row)
    return {"closes": closes, "snapshot": headline, "supplementary": supplementary}
