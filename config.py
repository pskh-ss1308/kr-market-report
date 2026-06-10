"""설정 로더: 환경변수에서 모든 설정을 읽어온다."""
import os
from dotenv import load_dotenv

load_dotenv()


def _split(v):
    return [x.strip() for x in (v or "").split(",") if x.strip()]


# ===== 운영 모드 =====
# true  → 시뮬레이션: Claude API·KIS API 호출 없음, 비용 0원
# false → 실전: 모든 API 호출
SIMULATION_MODE = os.getenv("SIMULATION_MODE", "true").lower() == "true"

# ===== KIS OpenAPI (수급·섹터) =====
KIS_APP_KEY    = os.getenv("KIS_APP_KEY", "")
KIS_APP_SECRET = os.getenv("KIS_APP_SECRET", "")

# ===== Claude API (SIMULATION_MODE=false 일 때만 사용) =====
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL      = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# ===== 분석 파라미터 =====
CORR_LOOKBACK     = int(os.getenv("CORR_LOOKBACK", "60"))
TOP_SECTORS       = int(os.getenv("TOP_SECTORS", "5"))
MAX_NEWS_PER_FEED = int(os.getenv("MAX_NEWS_PER_FEED", "6"))

# ===== 이메일 =====
EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASS     = os.getenv("SMTP_PASS", "")
EMAIL_TO      = _split(os.getenv("EMAIL_TO", ""))

# ===== Slack =====
SLACK_ENABLED     = os.getenv("SLACK_ENABLED", "false").lower() == "true"
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# ===== 뉴스 RSS =====
DEFAULT_RSS_KR = [
    "https://www.hankyung.com/feed/finance",
    "https://www.hankyung.com/feed/economy",
    "https://www.yna.co.kr/rss/economy.xml",
]
DEFAULT_RSS_US = [
    "https://feeds.marketwatch.com/marketwatch/topstories/",
    "https://finance.yahoo.com/news/rssindex",
    "https://search.cnbc.com/rss/2.0/id/100003114/device/rss/rss.html",
]
NEWS_RSS_KR = _split(os.getenv("NEWS_RSS_KR", "")) or DEFAULT_RSS_KR
NEWS_RSS_US = _split(os.getenv("NEWS_RSS_US", "")) or DEFAULT_RSS_US
