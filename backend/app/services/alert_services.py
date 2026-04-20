"""
FILE: backend/app/services/alert_service.py
==================================================
Alert Service — Email Notifications
==================================================

WHY A SEPARATE SERVICE LAYER?

  The "service layer" pattern keeps business logic OUT of route handlers.
  Route handlers should be thin — they receive a request, call a service,
  and return a response.  All complex logic lives in services.

  Benefits:
    - Services can be tested without an HTTP context
    - Services can be reused by multiple routes
    - Easier to swap implementations (e.g. switch email providers)

DEPENDENCY INVERSION PRINCIPLE:
  The route doesn't know HOW alerts are sent — it just calls AlertService.send_alert().
  If we switch from SMTP to SendGrid, only this file changes.

INTERVIEW TALKING POINT:
  "I separated the service layer from the route layer following SOLID principles.
  The route handler doesn't know how emails work — it just calls send_alert().
  This made it trivial to mock the service in unit tests."
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config.settings import settings


class AlertService:
    """
    Handles all alert notifications triggered by new accident events.

    This class uses static methods because it has no instance state —
    it's a namespace for related functions, not an object with data.
    """

    @staticmethod
    async def send_alert(accident) -> None:
        """
        Main entry point called from the accident creation route.
        Dispatches to all configured notification channels.

        Using async def because callers await it, and future implementations
        may include async HTTP calls (e.g. SendGrid, Twilio API).
        """
        print(
            f"📧 Sending alert for accident #{accident.id} "
            f"at {accident.location} [{accident.severity.upper()}]"
        )

        # Only attempt email if SMTP is configured
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            AlertService._send_email(accident)
        else:
            print("   ℹ️  Email not configured — set SMTP_USER and SMTP_PASSWORD in .env")

    @staticmethod
    def _send_email(accident) -> None:
        """
        Send an HTML email to emergency team operators via SMTP.

        Uses Python's built-in smtplib with STARTTLS for encryption.
        STARTTLS upgrades a plain connection to an encrypted one (port 587).
        SSL would use port 465 with smtplib.SMTP_SSL().

        In production, replace with an email service SDK (SendGrid, AWS SES)
        for better deliverability, bounce handling, and tracking.
        """
        # Severity → hex colour for the email template
        severity_colours = {
            "critical": "#FF2D2D",
            "high":     "#FF7A00",
            "medium":   "#FFD600",
            "low":      "#00E676",
        }
        colour = severity_colours.get(accident.severity, "#888888")

        subject = (
            f"🚨 [{accident.severity.upper()}] Accident Detected — {accident.location}"
        )

        # Plain-text fallback for email clients that don't render HTML
        text_body = f"""
EMERGENCY ALERT — ACCIDENT DETECTED

Location  : {accident.location}
Severity  : {accident.severity.upper()}
AI Score  : {(accident.confidence or 0) * 100:.0f}% confidence
Camera    : {accident.camera_id or 'Unknown'}
Detected  : {accident.detected_at}

Open Dashboard: http://localhost:5173/dashboard
        """.strip()

        # HTML email for modern clients
        html_body = f"""
        <html><body style="font-family: Arial, sans-serif; background: #0a0e1a; color: #e0eaf8; padding: 20px;">
          <div style="max-width: 500px; margin: auto; background: #0f1628; border: 2px solid {colour};
               border-radius: 8px; padding: 24px;">
            <h2 style="color: {colour}; margin: 0 0 16px;">🚨 ACCIDENT DETECTED</h2>
            <table style="width: 100%; border-collapse: collapse;">
              <tr><td style="color: #8899aa; padding: 4px 0;">Location</td>
                  <td style="font-weight: bold;">{accident.location}</td></tr>
              <tr><td style="color: #8899aa; padding: 4px 0;">Severity</td>
                  <td style="color: {colour}; font-weight: bold;">{accident.severity.upper()}</td></tr>
              <tr><td style="color: #8899aa; padding: 4px 0;">AI Confidence</td>
                  <td>{(accident.confidence or 0) * 100:.0f}%</td></tr>
              <tr><td style="color: #8899aa; padding: 4px 0;">Camera</td>
                  <td>{accident.camera_id or 'Unknown'}</td></tr>
              <tr><td style="color: #8899aa; padding: 4px 0;">Time</td>
                  <td>{accident.detected_at}</td></tr>
            </table>
            <a href="http://localhost:5173/dashboard"
               style="display: inline-block; margin-top: 16px; padding: 10px 20px;
                      background: {colour}; color: white; text-decoration: none;
                      border-radius: 4px; font-weight: bold;">
              Open Dashboard →
            </a>
          </div>
        </body></html>
        """

        # Build MIME message with both text and HTML parts
        # Email clients render HTML if supported, fall back to text
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = settings.SMTP_USER
        msg["To"]      = settings.SMTP_USER  # Production: use a distribution list

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body,  "html"))

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.ehlo()            # Identify ourselves to the server
                server.starttls()        # Upgrade to encrypted connection
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            print("   ✅ Alert email sent successfully")
        except smtplib.SMTPException as e:
            # Don't crash the endpoint if email fails — just log the error
            print(f"   ⚠️  Email send failed: {e}")
