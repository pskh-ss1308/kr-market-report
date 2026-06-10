# 국내 증시 데일리 레포트 — 세팅 가이드

> **목표**: 매 평일 오후 4시 30분, 코스피·코스닥 분석 레포트가 자동 생성됩니다.
> 코딩 경험이 없어도 괜찮습니다. 순서대로만 따라가세요.

---

## 전체 흐름

```
PHASE 1 (비용 0원)          PHASE 2 (실전)
───────────────────         ─────────────────────
데이터 수집 검증             Claude AI 분석 추가
이메일·Slack 발송 검증       API 키 등록
디자인 확인                  변수 1개 변경 → 완료
1~2주 시뮬레이션
```

**PHASE 1은 Anthropic API 키가 없어도 실행됩니다.**
데이터가 제대로 들어오는지, 이메일이 잘 가는지 무료로 검증한 뒤
확인되면 변수 하나만 바꿔서 실전으로 전환합니다.

---

## 준비물 체크리스트

| 필요한 것 | PHASE 1 | PHASE 2 |
|---|---|---|
| 컴퓨터 (Windows / Mac) | 필수 | 필수 |
| GitHub 계정 (무료) | 필수 | 필수 |
| Anthropic 계정 + API 키 | ❌ 불필요 | ✅ 필요 |
| 이메일·Slack | 선택 | 선택 |

---

# PHASE 1 — 시뮬레이션 (비용 0원)

## 1단계: Python 설치 확인

**Windows** — `윈도우키 + R` → `cmd` 입력 → 확인:
```
python --version
```

**Mac** — `Finder → 응용프로그램 → 유틸리티 → 터미널`:
```
python3 --version
```

`Python 3.9` 이상이 나오면 ✅ 다음 단계로.
오류가 나오면 **https://www.python.org/downloads** 에서 설치.
> ⚠️ Windows 설치 시 **`Add Python to PATH`** 체크 필수!

---

## 2단계: GitHub 계정 만들기

1. **https://github.com** → `Sign up`
2. 이메일, 비밀번호, 사용자 이름 입력 후 가입
3. 이메일 인증 → 로그인

---

## 3단계: 프로젝트 파일 준비

1. `kr-market-report.zip` 을 바탕화면에 저장
2. 압축 해제:
   - Windows: 파일 우클릭 → `압축 풀기` → 바탕화면
   - Mac: 파일 더블클릭

3. 터미널(명령창)에서 폴더로 이동:

**Windows:**
```cmd
cd %USERPROFILE%\Desktop\kr-market-report
```
**Mac:**
```bash
cd ~/Desktop/kr-market-report
```

`dir` (Windows) 또는 `ls` (Mac) 입력 시 `main.py`, `src` 폴더가 보이면 정상.

---

## 4단계: 패키지 설치

**Windows:**
```cmd
pip install -r requirements.txt
```
**Mac:**
```bash
pip3 install -r requirements.txt
```
1~3분 소요. 글자가 쭉 흐르는 건 정상. 마지막에 오류 없으면 완료.

---

## 5단계: 설정 파일(.env) 만들기

`.env.example` 파일을 복사해서 `.env` 로 이름을 바꾸세요.

**Windows:**
```cmd
copy .env.example .env
```
**Mac:**
```bash
cp .env.example .env
```

`.env` 파일을 메모장(또는 텍스트 편집기)으로 열면 아래와 같이 되어 있습니다:

```
SIMULATION_MODE=true          ← 이 상태 그대로 두세요 (Phase 1)
ANTHROPIC_API_KEY=            ← Phase 1에서는 비워둬도 됩니다
...
```

**지금은 아무것도 수정하지 않아도 됩니다.**
이메일·Slack 발송을 시뮬레이션 단계에서 함께 검증하고 싶다면
`EMAIL_ENABLED=true` 로 바꾸고 아래 항목을 채우세요 (선택).

---

## 6단계: 로컬에서 첫 실행 (시뮬레이션)

**Windows:**
```cmd
python main.py --force
```
**Mac:**
```bash
python3 main.py --force
```

정상 실행 시 이런 메시지가 출력됩니다:
```
[모드] 🔵 시뮬레이션
[1/6] 시장 데이터 수집…
[2/6] 수급 수집…
[3/6] 섹터·뉴스 수집…
[4/6] 상관관계 산출…
[5/6] 레포트 생성…
     └─ 시뮬레이션 템플릿 사용 (API 비용 없음)
[6/6] 렌더링 & 발송…
  - reports/2026-06-10.md
  - reports/2026-06-10.html
완료 (🔵 시뮬레이션)
```

`reports/오늘날짜.html` 을 브라우저로 열어서 레포트 구조와 데이터를 확인하세요.

> 레포트 상단에 **[시뮬레이션 모드]** 안내가 표시됩니다.
> 데이터(지수·수급·섹터·뉴스)는 실제 수집된 값이고, AI 분석만 없는 상태입니다.

---

## 오류 해결

| 오류 메시지 | 원인 | 해결 |
|---|---|---|
| `ModuleNotFoundError` | 패키지 미설치 | `pip install -r requirements.txt` 재실행 |
| `No module named 'pykrx'` | pykrx 설치 안됨 | `pip install pykrx` |
| 지수 데이터 없음 / 종료 | 오늘 휴장일 | `--force` 옵션 확인, 정상 동작 |
| 뉴스 수집 실패 로그 | RSS 주소 변경 | 해당 피드만 스킵하고 계속 진행됨 (정상) |

---

## 7단계: GitHub에 코드 올리기

### Git 설치 확인
```
git --version
```
오류 시 **https://git-scm.com/downloads** 에서 설치.

### 새 레포지토리 생성
1. **https://github.com** 로그인
2. 우측 상단 `+` → `New repository`
3. 이름: `kr-market-report` / **Private** 선택 / `Create repository`

### 코드 업로드 (아래를 한 줄씩 순서대로 입력)

```bash
git init
git add .
git commit -m "첫 번째 커밋"
git branch -M main
```

아래 명령에서 `[내GitHub아이디]` 를 본인 GitHub 아이디로 교체:
```bash
git remote add origin https://github.com/[내GitHub아이디]/kr-market-report.git
git push -u origin main
```

> 💡 비밀번호를 묻는다면 일반 비밀번호 대신 **Personal Access Token** 을 입력해야 합니다.
> **https://github.com/settings/tokens** → `Generate new token (classic)` → `repo` 체크 → 생성
> 생성된 토큰을 복사해서 비밀번호 자리에 붙여넣기.

---

## 8단계: GitHub Variables 등록 (시뮬레이션 모드로)

1. GitHub `kr-market-report` 레포 → 상단 `Settings`
2. 좌측 `Secrets and variables` → `Actions`
3. **`Variables` 탭** 클릭 → `New repository variable` 로 아래 등록:

| Name | Value | 설명 |
|---|---|---|
| `SIMULATION_MODE` | `true` | Phase 1: 시뮬레이션 |

이메일·Slack 발송을 지금 검증하고 싶다면 추가 등록:

| Name | Value |
|---|---|
| `EMAIL_ENABLED` | `true` |
| `EMAIL_TO` | 받을이메일@gmail.com |
| `SMTP_HOST` | smtp.gmail.com |
| `SMTP_PORT` | 587 |
| `SLACK_ENABLED` | `true` |

**`Secrets` 탭** → 이메일 발송 시 아래 등록:

| Name | Secret |
|---|---|
| `SMTP_USER` | 내Gmail주소@gmail.com |
| `SMTP_PASS` | Gmail 앱 비밀번호 (아래 참조) |
| `SLACK_WEBHOOK_URL` | Slack 웹훅 URL |

---

## Gmail 앱 비밀번호 발급 방법

1. **https://myaccount.google.com/security** → `2단계 인증` 활성화
2. **https://myaccount.google.com/apppasswords** 접속
3. `앱 선택 → 메일` / `기기 선택 → Windows 컴퓨터` → `생성`
4. 16자리 코드를 `SMTP_PASS` 에 입력 (공백 없이)

---

## 9단계: GitHub Actions에서 수동 실행 (시뮬레이션)

1. GitHub `kr-market-report` 레포 → 상단 `Actions` 탭
2. 좌측 `daily-market-report` 클릭
3. 우측 `Run workflow` 버튼 클릭
4. `force` ✅ 체크 → `Run workflow`
5. 약 2~3분 후 결과:
   - ✅ 초록 체크 = 성공
   - ❌ 빨간 X = 실패 (클릭해서 로그 확인)

성공 시 `Artifacts` 에서 `market-report-N` 다운로드 → HTML 파일로 레포트 확인.

이후 **매 평일 16:30 KST 자동 실행**됩니다 (시뮬레이션 모드).

---

## 시뮬레이션 기간 동안 확인할 것

1~2주 시뮬레이션을 돌리면서 아래를 체크하세요.

- [ ] 지수 데이터(코스피·코스닥·SOX·환율 등)가 정상 수집되는가
- [ ] 수급(외국인·기관·개인 순매수)이 나오는가
- [ ] 섹터 등락·거래대금이 나오는가
- [ ] 뉴스 헤드라인이 수집되는가
- [ ] 이메일이 정상 수신되는가
- [ ] Slack 메시지가 오는가
- [ ] HTML 레포트 디자인이 마음에 드는가
- [ ] 매일 16:30에 자동 실행되는가 (Actions 탭에서 확인)

모두 체크되면 → **PHASE 2로 전환**

---

# PHASE 2 — 실전 전환

> PHASE 1 체크리스트를 다 확인한 뒤 진행하세요.

## 10단계: Anthropic API 키 발급

1. **https://console.anthropic.com** 접속 → 가입 및 로그인
2. 상단 메뉴 `API Keys` → `+ Create Key`
3. 이름 입력 (예: `kr-market-report`) → `Create Key`
4. 화면에 표시된 키(`sk-ant-...`) **반드시 복사해서 저장**
   > ⚠️ 창을 닫으면 다시 볼 수 없습니다!

## 11단계: 결제 수단 등록

1. 콘솔 좌측 `Plans & Billing` → `Billing`
2. 신용카드 등록 → 크레딧 충전 (최소 $5 / 약 7,000원)
   > 💡 하루 1회 실행 기준 월 약 $0.2~0.6 (300~900원) 예상

---

## 12단계: GitHub에 API 키 등록

1. GitHub `kr-market-report` → `Settings` → `Secrets and variables` → `Actions`
2. **`Secrets` 탭** → `New repository secret`:

| Name | Secret |
|---|---|
| `ANTHROPIC_API_KEY` | sk-ant-... (발급받은 키) |

---

## 13단계: 실전 모드로 전환 (변수 1개 변경)

1. **`Variables` 탭** → `SIMULATION_MODE` 클릭 → `Edit`
2. 값을 `true` → **`false`** 로 변경 → 저장

끝입니다. 다음 자동 실행부터 Claude AI 분석이 포함된 실전 레포트가 생성됩니다.

---

## 14단계: 실전 전환 후 수동 테스트 (최종 확인)

1. `Actions` → `daily-market-report` → `Run workflow`
2. `force` ✅ / `simulation_override` → **`false`** 선택 → `Run workflow`
3. 완료 후 레포트 확인:
   - `[시뮬레이션 모드]` 안내문이 없어지고
   - Claude AI가 작성한 시나리오·분석이 채워져 있으면 성공

---

## 전체 요약

```
PHASE 1 (비용 0원)
  1단계  Python 설치 확인
  2단계  GitHub 계정 생성
  3단계  zip 파일 압축 해제
  4단계  pip install -r requirements.txt
  5단계  .env 파일 생성 (SIMULATION_MODE=true, 나머지 그대로)
  6단계  python main.py --force  →  reports/ 폴더 HTML 확인
  7단계  GitHub 레포 생성 + 코드 push
  8단계  GitHub Variables 등록 (SIMULATION_MODE=true)
  9단계  Actions에서 Run workflow → 시뮬레이션 검증 (1~2주)

PHASE 2 (실전 전환)
  10단계  Anthropic 계정 가입 + API 키 발급
  11단계  결제 수단 등록 ($5 충전)
  12단계  GitHub Secrets에 ANTHROPIC_API_KEY 등록
  13단계  Variables에서 SIMULATION_MODE → false 변경
  14단계  Run workflow로 최종 확인
          → 이후 매 평일 16:30 자동 실행 ✅
```

---

## FAQ

**Q. 시뮬레이션에서도 실제 시장 데이터가 수집되나요?**
A. 예. 지수·수급·섹터·뉴스 데이터는 모두 실제 수집됩니다. AI 분석만 없는 상태입니다.

**Q. PHASE 2 전환 후 되돌릴 수 있나요?**
A. 언제든지 가능합니다. Variables에서 `SIMULATION_MODE=true` 로 되돌리면 됩니다.

**Q. API 키가 노출될까 걱정돼요.**
A. GitHub Secrets는 암호화 저장됩니다. `.env` 파일은 `.gitignore` 처리되어 GitHub에 올라가지 않습니다.

**Q. 매일 정확히 16:30에 실행되나요?**
A. GitHub Actions 특성상 서버 부하에 따라 수 분 지연될 수 있습니다. 정확한 시간이 중요하다면 자체 서버 cron 또는 클라우드 스케줄러 연동을 권장합니다.

**Q. 공휴일에는 어떻게 되나요?**
A. KRX 데이터가 없으면 자동으로 종료됩니다. 별도 처리 없이도 공휴일 스킵이 됩니다.

**Q. 비용이 얼마나 드나요?**
A. PHASE 1은 완전 무료입니다. PHASE 2는 Claude API 사용료만 부과됩니다. 하루 1회 기준 월 약 300~900원 예상. GitHub Actions는 Private 레포 기준 월 2,000분 무료 (이 프로그램 1회 약 3분 = 월 60분 사용).
