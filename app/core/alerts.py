import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings


def send_alert(subject: str, body: str) -> None:
    """Send a failure alert email. Silently no-ops if alerts are disabled or misconfigured."""
    if not settings.ALERTS_ENABLED:
        return
    if not settings.ALERT_EMAIL_FROM or not settings.ALERT_EMAIL_PASSWORD:
        return

    try:
        msg = MIMEMultipart()
        msg["From"] = settings.ALERT_EMAIL_FROM
        msg["To"] = settings.ALERT_EMAIL_TO
        msg["Subject"] = f"[CrewSignal Alert] {subject}"
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(settings.ALERT_EMAIL_FROM, settings.ALERT_EMAIL_PASSWORD)
            server.sendmail(settings.ALERT_EMAIL_FROM, settings.ALERT_EMAIL_TO, msg.as_string())
    except Exception as exc:
        print(f"[ALERTS] Failed to send alert email: {exc}")
