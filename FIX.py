import os, sys

# ── collect_market.py ──────────────────────────────────────────
COLLECT = r"""from __future__ import annotations
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
"""

# ── correlations.py ────────────────────────────────────────────
CORR = r"""from __future__ import annotations
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
"""

# ── 실제 파일 쓰기 ─────────────────────────────────────────────
os.makedirs("src", exist_ok=True)

target = os.path.join("src", "collect_market.py")
with open(target, "w", encoding="utf-8") as f:
    f.write(COLLECT.lstrip("\n"))
print(f"✅ {target} 교체 완료")

target = os.path.join("src", "correlations.py")
with open(target, "w", encoding="utf-8") as f:
    f.write(CORR.lstrip("\n"))
print(f"✅ {target} 교체 완료")

# ── 구문 검사 ──────────────────────────────────────────────────
import py_compile
for p in ["src/collect_market.py", "src/correlations.py"]:
    py_compile.compile(p, doraise=True)
    print(f"✅ {p} 구문 OK")

print()
print("모두 완료! 이제 실행하세요:")
print("  python main.py --force")
