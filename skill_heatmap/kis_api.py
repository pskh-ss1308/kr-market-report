"""
KIS API 래퍼 — 일봉 OHLCV + 종목 리스트 조회
환경변수: KIS_APP_KEY, KIS_APP_SECRET
"""

import os
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from functools import lru_cache

BASE_URL = "https://openapi.koreainvestment.com:9443"

class KisAPI:
    def __init__(self):
        self.app_key    = os.environ["KIS_APP_KEY"]
        self.app_secret = os.environ["KIS_APP_SECRET"]
        self._token     = None
        self._token_exp = None

    def _get_token(self) -> str:
        if self._token and datetime.now() < self._token_exp:
            return self._token
        resp = requests.post(
            f"{BASE_URL}/oauth2/tokenP",
            json={
                "grant_type": "client_credentials",
                "appkey":     self.app_key,
                "appsecret":  self.app_secret,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token     = data["access_token"]
        self._token_exp = datetime.now() + timedelta(hours=23)
        return self._token

    def _headers(self, tr_id: str) -> dict:
        return {
            "Content-Type":  "application/json; charset=utf-8",
            "authorization": f"Bearer {self._get_token()}",
            "appkey":        self.app_key,
            "appsecret":     self.app_secret,
            "tr_id":         tr_id,
            "custtype":      "P",
        }

    def get_daily_ohlcv(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        url    = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD":         ticker,
            "FID_INPUT_DATE_1":       start,
            "FID_INPUT_DATE_2":       end,
            "FID_PERIOD_DIV_CODE":    "D",
            "FID_ORG_ADJ_PRC":        "0",
        }
        resp = requests.get(url, headers=self._headers("FHKST03010100"), params=params, timeout=15)
        resp.raise_for_status()
        raw  = resp.json().get("output2", [])
        if not raw:
            return pd.DataFrame()
        df = pd.DataFrame(raw)
        df = df.rename(columns={
            "stck_bsop_date": "date",
            "stck_oprc":      "open",
            "stck_hgpr":      "high",
            "stck_lwpr":      "low",
            "stck_clpr":      "close",
            "acml_vol":       "volume",
        })[["date","open","high","low","close","volume"]]
        df[["open","high","low","close","volume"]] = df[["open","high","low","close","volume"]].apply(pd.to_numeric, errors="coerce")
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        return df

    def get_ticker_list(self, market: str = "KOSPI") -> list[str]:
        SAMPLE_KOSPI = [
            "005930","000660","051910","005380","035420",
            "000270","068270","105560","028260","012330",
            "003550","034730","018260","032830","096770",
            "017670","055550","316140","086790","033780",
            "003490","010130","138040","009150","011070",
            "024110","047050","015760","034020","011780",
            "042660","009540","000810","161390","004020",
            "006400","207940","352820","259960","035720",
        ]
        SAMPLE_KOSDAQ = [
            "247540","091990","196170","086520","035900",
            "112040","263750","357780","039030","145020",
            "066970","950130","031980","241560","036930",
            "293490","263920","240810","122870","041510",
        ]
        return SAMPLE_KOSPI if market == "KOSPI" else
