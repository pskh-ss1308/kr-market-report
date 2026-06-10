# 국내 증시 데일리 분석 레포트 (KOSPI · KOSDAQ)

매 거래일 **16:30 KST**, 당일 시장 분석 + 익일 시나리오 레포트를 자동 생성·발송합니다.
GitHub Actions(cron) + Python + Claude API 로 동작하며 별도 서버가 필요 없습니다.

## 레포트 구성
1. 오늘 시장 한눈에 (코스피·코스닥 종가·등락 + 수급 요약)
2. **수급 & 거래대금** (외국인·기관·개인 순매수 / 총 거래대금)
3. 국내·미국 뉴스 & 지수 상관관계
4. 오늘 주목받은 섹터 (**거래대금=주목도**, 등락률=강세/약세 분리)
5. 내일 시장 시나리오 (상승/중립/하락 + 확률 + 체크포인트)
6. 한 줄 요약 & 면책

> 모든 수치·뉴스에 출처를 표기하고, '내일 예측'은 단정이 아닌 시나리오·확률로 제시합니다. 투자 자문이 아닙니다.

## 분석에 쓰는 데이터 & 출처
- 지수: 코스피·코스닥·KOSPI200 (**KRX**), S&P500·나스닥·다우·**SOX(필라델피아 반도체)**·VIX (**Yahoo Finance**)
- 환율·금리·원자재: 원/달러(FDR FX), **미국채 10년물·달러인덱스·WTI** (**FRED**, API 키 불필요)
- 수급: 외국인·기관·개인 순매수, 거래대금 (**KRX 투자자별 거래대금**)
- 섹터: KRX 업종지수 등락률·거래대금
- 뉴스: 한국경제(증권·경제, 공식 RSS 확인) + 연합뉴스(best-effort) + MarketWatch·Yahoo·CNBC
- 분석: **Anthropic Claude** (`claude-sonnet-4-6`)

## 로컬 실행
```bash
pip install -r requirements.txt
cp .env.example .env          # 최소 ANTHROPIC_API_KEY 입력
python main.py --force        # 휴장 가드 무시하고 즉시 1회 생성
```
결과물: `reports/<날짜>.md`, `reports/<날짜>.html`

## GitHub Actions 설정
Settings → Secrets and variables → Actions:
- **Secrets**: `ANTHROPIC_API_KEY`(필수), `SMTP_USER`/`SMTP_PASS`(메일), `SLACK_WEBHOOK_URL`(슬랙)
- **Variables**: `EMAIL_ENABLED`,`EMAIL_TO`,`SMTP_HOST`,`SMTP_PORT`,`SLACK_ENABLED`,`CLAUDE_MODEL`

스케줄: `.github/workflows/daily-report.yml` 의 cron `30 7 * * 1-5` (= 16:30 KST). 수동 실행은 Actions → Run workflow.

## 알려진 한계 / 운영 팁
- **정시성**: GitHub Actions 예약 작업은 부하 시 수 분~수십 분 지연되거나 드물게 누락될 수 있습니다(GitHub 구조적 특성). "정확히 16:30"이 중요하면 외부 스케줄러(클라우드 스케줄러·자체 서버 cron 등)에서 `python main.py` 를 호출하는 방식이 더 정확합니다.
- **익일 예측의 본질적 한계**: 레포트는 16:30 KST, 즉 **오늘 밤 미국 정규장이 열리기 전**에 작성됩니다. 내일 한국 개장의 최대 변수인 오늘 밤 미국장은 미발생 상태이므로, 예측은 전일 미국 종가·당일 한국 수급·환율 기반이며 체크포인트에 이 점을 명시합니다.
- **뉴스**: 헤드라인(제목+링크) 기준 분석입니다. 본문 전체를 읽지는 않습니다. RSS 주소는 매체 사정으로 변경될 수 있어 실패 시 해당 피드만 건너뜁니다(`NEWS_RSS_KR/US` 로 교체 가능). 한국경제 피드는 공식 RSS 목록에서 확인했고, 연합뉴스는 미검증 best-effort입니다.
- **pykrx**: KRX 사이트 구조 변경에 영향받을 수 있어 수급·섹터는 일괄→개별 조회 이중화를 했습니다. 첫 실행 로그를 꼭 확인하세요.
- **공휴일**: 데이터 미반영 기준으로 자동 스킵합니다. 정밀 휴장 캘린더가 필요하면 `holidays` 연동 권장.
- '내일 시나리오'는 확률적 분석이며 수익을 보장하지 않습니다.
