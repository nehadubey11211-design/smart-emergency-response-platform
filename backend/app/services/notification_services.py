"""
FILE: backend/app/services/notification_service.py
=========================================================
Notification Service — Extensible Multi-Channel Dispatcher
=========================================================

OPEN/CLOSED PRINCIPLE:
  This service is designed to be extended without modifying existing code.
  To add a new notification channel (e.g. WhatsApp, PagerDuty, webhook):
    1. Add a new static method (e.g. _send_pagerduty)
    2. Call it from notify_all()
  You never need to touch the accident route or any other existing code.

CHANNELS SUPPORTED:
  ✅ Console logging     (always active — for debugging)
  ⬜ SMS via Twilio      (stub — uncomment and configure)
  ⬜ Slack webhook       (stub — uncomment and configure)
  ⬜ Push notification   (stub — for mobile app integration)
"""

import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)


class NotificationService:

    @staticmethod
    async def notify_all(accident) -> None:
        """
        Dispatch to all enabled notification channels.
        Failures in individual channels are caught and logged — one failing
        channel should NOT prevent others from running.
        """
        channels = [
            ("Console", NotificationService._log_to_console),
            # Uncomment to enable:
            # ("SMS",    NotificationService._send_sms),
            # ("Slack",  NotificationService._send_slack),
        ]

        for channel_name, channel_fn in channels:
            try:
                await channel_fn(accident)
            except Exception as e:
                # Log the failure but continue with other channels
                logger.warning("Notification channel '%s' failed: %s", channel_name, e)

    @staticmethod
    async def _log_to_console(accident) -> None:
        """
        Structured console log.
        In production, replace with structured logging (e.g. structlog or loguru)
        to produce JSON logs that are parseable by tools like Datadog or Splunk.
        """
        logger.info(
            "INCIDENT #%04d | %s | location=%s | camera=%s | confidence=%.0f%% | at=%s",
            accident.id,
            accident.severity.upper(),
            accident.location,
            accident.camera_id or "Unknown",
            (accident.confidence or 0) * 100,
            accident.detected_at.strftime("%d %b %H:%M:%S"),
        )

    @staticmethod
    async def _send_sms(accident) -> None:
        """
        Send an SMS alert via Twilio.

        TO ENABLE:
          1. pip install twilio
          2. Add to .env:
               TWILIO_SID=ACxxxxxxx
               TWILIO_TOKEN=xxxxxxx
               TWILIO_FROM=+1234567890
               EMERGENCY_PHONE=+0987654321
          3. Uncomment this method call in notify_all()

        Twilio's REST API wraps the SMS protocol — no carrier agreements needed.
        """
        # from twilio.rest import Client
        # client = Client(settings.TWILIO_SID, settings.TWILIO_TOKEN)
        # message = client.messages.create(
        #     body=(
        #         f"🚨 [{accident.severity.upper()}] Accident at {accident.location}. "
        #         f"AI confidence: {(accident.confidence or 0)*100:.0f}%. "
        #         f"Dashboard: http://localhost:5173/dashboard"
        #     ),
        #     from_=settings.TWILIO_FROM,
        #     to=settings.EMERGENCY_PHONE,
        # )
        # print(f"   📱 SMS sent: {message.sid}")
        pass

    @staticmethod
    async def _send_slack(accident) -> None:
        """
        Send a Slack message via an Incoming Webhook.

        TO ENABLE:
          1. pip install httpx
          2. Add to .env: SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
          3. Uncomment this method call in notify_all()

        Slack Incoming Webhooks are a simple way to post messages without OAuth.
        """
        # import httpx
        # if not getattr(settings, "SLACK_WEBHOOK_URL", ""):
        #     return
        # severity_colours = {"critical":"danger","high":"warning","medium":"warning","low":"good"}
        # payload = {
        #     "attachments": [{
        #         "color": severity_colours.get(accident.severity, "warning"),
        #         "title": f"🚨 [{accident.severity.upper()}] Accident Detected",
        #         "fields": [
        #             {"title": "Location",   "value": accident.location,                   "short": True},
        #             {"title": "Confidence", "value": f"{(accident.confidence or 0)*100:.0f}%", "short": True},
        #             {"title": "Camera",     "value": accident.camera_id or "Unknown",      "short": True},
        #         ],
        #         "footer": "AI Emergency Response System",
        #         "ts": int(accident.detected_at.timestamp()),
        #     }]
        # }
        # async with httpx.AsyncClient() as client:
        #     await client.post(settings.SLACK_WEBHOOK_URL, json=payload)
        # print("   💬 Slack notification sent")
        pass
