"""발송: 이메일(SMTP, HTML 본문) / Slack(웹훅, 텍스트 요약)."""
from __future__ import annotations
import smtplib
import json
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config


def send_email(subject: str, html: str) -> bool:
    if not (config.EMAIL_ENABLED and config.EMAIL_TO and config.SMTP_USER):
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config.SMTP_USER
        msg["To"] = ", ".join(config.EMAIL_TO)
        msg.attach(MIMEText(html, "html", "utf-8"))
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as s:
            s.starttls()
            s.login(config.SMTP_USER, config.SMTP_PASS)
            s.sendmail(config.SMTP_USER, config.EMAIL_TO, msg.as_string())
        print(f"[deliver] 이메일 발송 완료 → {config.EMAIL_TO}")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[deliver] 이메일 발송 실패: {e}")
        return False


def send_slack(text: str) -> bool:
    if not (config.SLACK_ENABLED and config.SLACK_WEBHOOK_URL):
        return False
    try:
        # Slack 메시지 길이 제한 고려, 앞부분만
        payload = json.dumps({"text": text[:3500]}).encode("utf-8")
        req = urllib.request.Request(
            config.SLACK_WEBHOOK_URL, data=payload,
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=15)
        print("[deliver] Slack 발송 완료")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[deliver] Slack 발송 실패: {e}")
        return False
