"""KIS API 인증 — OAuth 접근토큰 발급 및 캐싱.

토큰 유효기간: 24시간. 하루 1회 실행 파이프라인이므로
매 실행 시 새 토큰을 발급한다(만료 체크 불필요).

출처: KIS Developers OAuth인증 > 접근토큰발급(P)
https://apiportal.koreainvestment.com
"""
from __future__ import annotations
import requests

KIS_BASE = "https://openapi.koreainvestment.com:9443"


def get_access_token(app_key: str, app_secret: str) -> str:
    """OAuth 접근토큰 발급. 실패 시 RuntimeError."""
    url = f"{KIS_BASE}/oauth2/tokenP"
    body = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret,
    }
    resp = requests.post(url, json=body, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    token = data.get("access_token", "")
    if not token:
        raise RuntimeError(f"KIS 토큰 발급 실패: {data}")
    return token


def kis_get(path: str, params: dict, app_key: str,
            access_token: str, tr_id: str) -> dict:
    """KIS REST API GET 공통 헬퍼."""
    url = f"{KIS_BASE}{path}"
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": app_key,
        "tr_id": tr_id,
    }
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()
