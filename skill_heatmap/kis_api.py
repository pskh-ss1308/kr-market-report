"""
FinanceDataReader 기반 OHLCV 조회
KIS API 대신 사용 (GitHub Actions 환경 호환)
"""

import pandas as pd
import FinanceDataReader as fdr
from datetime import date


class KisAPI:
    def __init__(self):
        pass  # 인증 불필요

    def get_daily_ohlcv(self, ticker, start, end, market="KR"):
        try:
            if market == "US":
                df = fdr.DataReader(ticker, start, end)
            else:
                df = fdr.DataReader(ticker, start, end)
            if df.empty:
                return pd.DataFrame()
            df = df.reset_index()
            df = df.rename(columns={
                "Date":   "date",
                "Open":   "open",
                "High":   "high",
                "Low":    "low",
                "Close":  "close",
                "Volume": "volume",
            })
            df = df[["date","open","high","low","close","volume"]]
            df[["open","high","low","close","volume"]] = df[["open","high","low","close","volume"]].apply(pd.to_numeric, errors="coerce")
            df["date"] = pd.to_datetime(df["date"])
            return df.sort_values("date").reset_index(drop=True)
        except Exception as e:
            print(f"[WARN] {ticker}: {e}")
            return pd.DataFrame()

    def get_ticker_list(self, market="KOSPI"):
        try:
            if market == "US":
                # S&P500 구성종목
                df = fdr.StockListing("S&P500")
                return df["Symbol"].dropna().tolist()[:50]
            else:
                # KOSPI 전종목
                df = fdr.StockListing("KOSPI")
                # 시가총액 상위 100개
                if "Marcap" in df.columns:
                    df = df.nlargest(100, "Marcap")
                return df["Code"].dropna().tolist()
        except Exception as e:
            print(f"[WARN] get_ticker_list {market}: {e}")
            # 폴백: 하드코딩 샘플
            if market == "US":
                return [
                    "AAPL","MSFT","NVDA","AMZN","META",
                    "GOOGL","TSLA","AVGO","AMD","ORCL",
                    "NFLX","CRM","ADBE","QCOM","INTC",
                    "MU","AMAT","LRCX","KLAC","MRVL",
                ]
            return [
                "005930","000660","051910","005380","035420",
                "000270","068270","105560","028260","012330",
                "003550","034730","018260","032830","096770",
                "017670","055550","316140","086790","033780",
            ]

    def batch_ohlcv(self, tickers, start, end, delay=0.1, market="KR"):
        result = {}
        for i, ticker in enumerate(tickers):
            df = self.get_daily_ohlcv(ticker, start, end, market=market)
            if not df.empty:
                result[ticker] = df
            if i % 20 == 19:
                import time
                time.sleep(0.5)
        return result
