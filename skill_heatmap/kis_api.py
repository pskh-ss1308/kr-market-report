"""
FinanceDataReader 기반 OHLCV 조회 + 종목명 매핑
"""

import time
import pandas as pd
import FinanceDataReader as fdr


class KisAPI:
    def __init__(self):
        self._kr_names = {}
        try:
            df = fdr.StockListing("KOSPI")
            self._kr_names = dict(zip(df["Code"].astype(str), df["Name"]))
            df2 = fdr.StockListing("KOSDAQ")
            self._kr_names.update(dict(zip(df2["Code"].astype(str), df2["Name"])))
            print(f"  종목명 로딩 완료: {len(self._kr_names)}개")
        except Exception as e:
            print(f"[WARN] 종목명 로딩 실패: {e}")

    def get_name(self, ticker, market="KR"):
        if market == "US":
            return ticker
        return self._kr_names.get(str(ticker), ticker)

    def get_daily_ohlcv(self, ticker, start, end):
        try:
            df = fdr.DataReader(ticker, start, end)
            if df is None or df.empty:
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
            cols = [c for c in ["date","open","high","low","close","volume"] if c in df.columns]
            df = df[cols]
            df[["open","high","low","close","volume"]] = df[["open","high","low","close","volume"]].apply(pd.to_numeric, errors="coerce")
            df["date"] = pd.to_datetime(df["date"])
            return df.sort_values("date").reset_index(drop=True)
        except Exception as e:
            print(f"[WARN] {ticker}: {e}")
            return pd.DataFrame()

    def get_ticker_list(self, market="KOSPI"):
        try:
            if market == "US":
                df = fdr.StockListing("S&P500")
                return df["Symbol"].dropna().tolist()[:50]
            else:
                df = fdr.StockListing("KOSPI")
                if "Marcap" in df.columns:
                    df = df.nlargest(100, "Marcap")
                return df["Code"].dropna().astype(str).tolist()
        except Exception as e:
            print(f"[WARN] get_ticker_list {market}: {e}")
            return [
                "005930","000660","051910","005380","035420",
                "000270","068270","105560","028260","012330",
                "003550","034730","018260","032830","096770",
                "017670","055550","316140","086790","033780",
            ]

    def batch_ohlcv(self, tickers, start, end, delay=0.1, market="KR"):
        result = {}
        for i, ticker in enumerate(tickers):
            df = self.get_daily_ohlcv(ticker, start, end)
            if not df.empty:
                result[ticker] = df
            if i % 20 == 19:
                time.sleep(0.5)
        return result
