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
            # 인덱스가 날짜인 경우 reset
            df = df.reset_index()
            # 컬럼명 소문자 통일
            df.columns = [c.lower() for c in df.columns]
            # 날짜 컬럼 찾기 (date 또는 index)
            date_col = None
            for c in ["date", "datetime", "time", "index"]:
                if c in df.columns:
                    date_col = c
                    break
            if date_col is None:
                print(f"[WARN] {ticker}: 날짜 컬럼 없음 {df.columns.tolist()}")
                return pd.DataFrame()
            if date_col != "date":
                df = df.rename(columns={date_col: "date"})
            # 필요 컬럼만 선택
            need = ["date","open","high","low","close","volume"]
            cols = [c for c in need if c in df.columns]
            df = df[cols]
            for c in cols:
                if c != "date":
                    df[c] = pd.to_numeric(df[c], errors="coerce")
            df["date"] = pd.to_datetime(df["date"])
            return df.sort_values("date").reset_index(drop=True)
        except Exception as e:
            print(f"[WARN] {ticker}: {e}")
            return pd.DataFrame()

    def get_ticker_list(self, market="KOSPI"):
        try:
            if market == "US":
                df = fdr.StockListing("S&P500")
                print(f"  S&P500 컬럼: {df.columns.tolist()}")
                # Symbol 또는 Code 컬럼
                sym_col = None
                for c in ["Symbol", "Code", "symbol", "code"]:
                    if c in df.columns:
                        sym_col = c
                        break
                if sym_col is None:
                    raise ValueError(f"심볼 컬럼 없음: {df.columns.tolist()}")
                return df[sym_col].dropna().tolist()[:50]
            else:
                df = fdr.StockListing("KOSPI")
                if "Marcap" in df.columns:
                    df = df.nlargest(100, "Marcap")
                return df["Code"].dropna().astype(str).tolist()
        except Exception as e:
            print(f"[WARN] get_ticker_list {market}: {e}")
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
