"""Claude API 호출로 분석 레포트 본문을 생성한다.

핵심 원칙(프롬프트에 강제):
  - 제공된 DATA 만 사용, 수치·사실 날조 금지
  - 모든 주장에 출처 표기
  - '내일 예측'은 단정이 아니라 시나리오+확률
  - 16:30 KST 생성 시점 한계(오늘 밤 미국장 미발생)를 반영
  - 투자 자문이 아님을 명시
출력은 마크다운(섹션 고정).
"""
from __future__ import annotations
import json
import datetime as dt
import anthropic

import config

SYSTEM = """당신은 한국 증시(코스피·코스닥) 데일리 분석가다. 아래 규칙을 반드시 지킨다.

1. 제공된 DATA 블록의 수치·수급·뉴스·상관계수만 근거로 사용한다. DATA에 없는 값을 만들지 않는다.
2. 모든 핵심 주장 끝에 (출처: ...) 를 단다. 지수=KRX/Yahoo Finance/FRED, 수급=KRX, 뉴스=매체명, 상관계수=계산값.
3. 수급(외국인·기관·개인 순매수, 단위 억원)을 반드시 해석에 활용한다 — 한국 데일리의 핵심 지표다.
4. 섹터는 두 축으로 구분한다: '주목 섹터'=거래대금(자금 쏠림) 상위, '강세/약세 섹터'=등락률 기준. 자금이 쏠린 이유는 추정임을 명시.
5. 상관계수 해석 시, 특히 SOX(필라델피아 반도체지수)와의 동조성을 반도체 비중이 큰 한국 시장 맥락에서 짚는다(데이터가 있을 때만).
6. '내일 시나리오'는 상승/중립/하락 3개로, 각 트리거와 확률(%)을 명시한다(합 100%). 단정 금지.
7. [중요] 이 레포트는 한국시간 16:30, 즉 오늘 밤 미국 정규장이 열리기 '전'에 작성된다. 따라서 내일 한국 개장의 최대 변수인 '오늘 밤 미국장'은 아직 미발생 상태다. 예측은 전일 미국 종가·당일 한국 수급·환율에 기반하며, 오늘 밤 미국장 결과에 따라 달라질 수 있음을 체크포인트에 명시한다.
8. DATA가 결측이면 "데이터 없음/제한적"으로 솔직히 적는다. 추측으로 메우지 않는다.
9. 톤은 간결·실무형, 한국어. 투자자가 바로 쓸 인사이트 중심.

출력 형식(마크다운, 제목 그대로):

## 1. 오늘 시장 한눈에
(코스피·코스닥 종가·등락 + 외국인/기관 수급 한 줄 + 핵심 동인 3줄 이내)

## 2. 수급 & 거래대금
(외국인·기관·개인 순매수 방향과 의미, 총 거래대금 수준)

## 3. 국내·미국 뉴스 & 지수 상관관계
- 미국/한국 주요 뉴스가 오늘 시장에 준 영향
- 상관계수 해석(SOX·S&P500·나스닥·환율·금리·유가 중 강하게 동행/역행한 것과 그 의미)

## 4. 오늘 주목받은 섹터
- 자금 쏠림(거래대금) 상위 섹터 = 주목 섹터
- 강세/약세(등락률) 섹터
- 쏠림 이유 추정(추정임을 명시)

## 5. 내일 시장 시나리오
- 상승 (확률 %): 트리거
- 중립 (확률 %): 트리거
- 하락 (확률 %): 트리거
- 체크포인트 (오늘 밤 미국장/선물·환율·예정 이벤트 — 미국장 미발생 한계 명시)

## 6. 한 줄 요약 & 면책
"""


def _data_block(bundle: dict) -> str:
    return json.dumps(bundle, ensure_ascii=False, indent=2, default=str)


def generate_report(bundle: dict) -> str:
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY 가 설정되지 않았습니다.")

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    today = dt.date.today().isoformat()
    user_msg = (
        f"오늘 날짜: {today} (작성 시각: 한국시간 16:30 가정)\n\n"
        f"아래 DATA만 근거로 데일리 레포트를 작성하라.\n\n"
        f"DATA:\n```json\n{_data_block(bundle)}\n```"
    )
    resp = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=3000,
        system=SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()
