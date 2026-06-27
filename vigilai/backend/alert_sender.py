"""Alert sender module for VigilAI.

Sends email and SMS notifications for suspicious activities.
Supports Gmail SMTP for email and Twilio for SMS.

Required packages (install before use):
  pip install python-dotenv twilio

Gmail setup:
  1. Enable 2FA on your Google account
  2. Generate an App Password at https://myaccount.google.com/apppasswords
  3. Use the 16-char app password (not your real password)

Twilio setup:
  1. Sign up at https://www.twilio.com
  2. Get your Account SID and Auth Token from the dashboard
  3. Buy a phone number or use the trial number
"""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime, timezone

from dotenv import load_dotenv
import os

load_dotenv()

logger = logging.getLogger(__name__)


class SendResult:
    """Structured result of a send attempt."""

    __slots__ = ("ok", "error")

    def __init__(self, ok: bool, error: str | None = None) -> None:
        self.ok = ok
        self.error = error


class AlertSender:
    """Handles sending email and SMS alerts for suspicious activities."""

    def __init__(self) -> None:
        # Gmail SMTP credentials
        self.gmail_user: str = os.getenv("GMAIL_USER", "")
        self.gmail_password: str = os.getenv("GMAIL_APP_PASSWORD", "")

        # Twilio credentials
        self.twilio_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.twilio_token: str = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.twilio_from: str = os.getenv("TWILIO_FROM", "")

        # Recipient contacts
        self.police_email: str = os.getenv("POLICE_EMAIL", "")
        self.police_phone: str = os.getenv("POLICE_PHONE", "")
        self.emergency_email: str = os.getenv("EMERGENCY_EMAIL", "")
        self.emergency_phone: str = os.getenv("EMERGENCY_PHONE", "")
        self.owner_email: str = os.getenv("OWNER_EMAIL", "")
        self.owner_phone: str = os.getenv("OWNER_PHONE", "")

    # ------------------------------------------------------------------ #
    #  Email
    # ------------------------------------------------------------------ #
    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        image_bytes: bytes | None = None,
    ) -> SendResult:
        """Send an email via Gmail SMTP.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            body: Plain-text body of the email.
            image_bytes: Optional JPEG/PNG screenshot to attach.

        Returns:
            SendResult with ok=True on success, else ok=False with error.
        """
        if not self.gmail_user or not self.gmail_password:
            return SendResult(False, "Gmail credentials not configured")

        try:
            msg = MIMEMultipart()
            msg["From"] = self.gmail_user
            msg["To"] = to
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "plain"))

            if image_bytes:
                img_attachment = MIMEImage(image_bytes)
                img_attachment.add_header(
                    "Content-Disposition", "attachment", filename="screenshot.jpg"
                )
                msg.attach(img_attachment)

            context = ssl.create_default_context()
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls(context=context)
                server.login(self.gmail_user, self.gmail_password)
                server.sendmail(self.gmail_user, to, msg.as_string())

            logger.info(f"Email sent to {to}: {subject}")
            return SendResult(True)

        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")
            return SendResult(False, str(e))

    # ------------------------------------------------------------------ #
    #  SMS
    # ------------------------------------------------------------------ #
    def send_sms(self, to: str, message: str) -> SendResult:
        """Send an SMS via Twilio.

        Args:
            to: Recipient phone number (E.164 format, e.g. +1234567890).
            message: SMS body text.

        Returns:
            SendResult with ok=True on success, else ok=False with error.
        """
        if not self.twilio_sid or not self.twilio_token or not self.twilio_from:
            return SendResult(False, "Twilio credentials not configured")

        try:
            from twilio.rest import Client

            client = Client(self.twilio_sid, self.twilio_token)
            sms = client.messages.create(
                body=message,
                from_=self.twilio_from,
                to=to,
            )
            logger.info(f"SMS sent to {to}: SID={sms.sid}")
            return SendResult(True)

        except Exception as e:
            logger.error(f"Failed to send SMS to {to}: {e}")
            return SendResult(False, str(e))

    # ------------------------------------------------------------------ #
    #  Alert: Police
    # ------------------------------------------------------------------ #
    def alert_police(
        self,
        activity_type: str,
        severity: str,
        location: str,
        image_bytes: bytes | None = None,
    ) -> dict:
        """Send alert to police — email + SMS.

        Returns:
            Dict with email_ok, sms_ok, error (first error or None).
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        subject = f"[VIGILAI ALERT] {severity} — {activity_type} at {location}"

        body = (
            f"VigilAI Security Alert\n"
            f"{'=' * 40}\n\n"
            f"Timestamp:  {timestamp}\n"
            f"Activity:   {activity_type.upper()}\n"
            f"Severity:   {severity}\n"
            f"Location:   {location}\n\n"
            f"Description:\n"
            f"A {severity.lower()} severity incident has been detected by the\n"
            f"VigilAI surveillance system. Immediate attention required.\n\n"
            f"Recommended Action:\n"
            f"Dispatch units to {location} immediately.\n\n"
            f"{'=' * 40}\n"
            f"VigilAI Automated Alert System\n"
        )

        sms_msg = (
            f"[VIGILAI] {severity} ALERT\n"
            f"{activity_type.upper()} at {location}\n"
            f"Time: {timestamp}\n"
            f"Immediate response required."
        )

        email_result = SendResult(False, "No police email configured")
        sms_result = SendResult(False, "No police phone configured")

        if self.police_email:
            email_result = self.send_email(
                self.police_email, subject, body, image_bytes
            )

        if self.police_phone:
            sms_result = self.send_sms(self.police_phone, sms_msg)

        error = email_result.error if not email_result.ok else sms_result.error
        return {
            "email_ok": email_result.ok,
            "sms_ok": sms_result.ok,
            "error": error,
        }

    # ------------------------------------------------------------------ #
    #  Alert: Emergency (Medical)
    # ------------------------------------------------------------------ #
    def alert_emergency(
        self,
        activity_type: str,
        location: str,
        image_bytes: bytes | None = None,
    ) -> dict:
        """Send alert to emergency services — email + SMS.

        Returns:
            Dict with email_ok, sms_ok, error.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        subject = f"[VIGILAI EMERGENCY] HIGH — {activity_type} at {location}"

        body = (
            f"VigilAI Emergency Alert\n"
            f"{'=' * 40}\n\n"
            f"Timestamp:  {timestamp}\n"
            f"Emergency:  {activity_type.upper()}\n"
            f"Severity:   HIGH\n"
            f"Location:   {location}\n\n"
            f"Description:\n"
            f"A medical emergency has been detected by the VigilAI\n"
            f"surveillance system. A person may be injured or in distress.\n\n"
            f"Recommended Action:\n"
            f"Dispatch medical emergency services to {location} immediately.\n"
            f"Check for injured persons and provide first aid if needed.\n\n"
            f"{'=' * 40}\n"
            f"VigilAI Automated Alert System\n"
        )

        sms_msg = (
            f"[VIGILAI] EMERGENCY ALERT\n"
            f"{activity_type.upper()} detected at {location}\n"
            f"Time: {timestamp}\n"
            f"Medical response required immediately."
        )

        email_result = SendResult(False, "No emergency email configured")
        sms_result = SendResult(False, "No emergency phone configured")

        if self.emergency_email:
            email_result = self.send_email(
                self.emergency_email, subject, body, image_bytes
            )

        if self.emergency_phone:
            sms_result = self.send_sms(self.emergency_phone, sms_msg)

        error = email_result.error if not email_result.ok else sms_result.error
        return {
            "email_ok": email_result.ok,
            "sms_ok": sms_result.ok,
            "error": error,
        }

    # ------------------------------------------------------------------ #
    #  Alert: Owner
    # ------------------------------------------------------------------ #
    def alert_owner(
        self,
        activity_type: str,
        severity: str,
        summary: str,
    ) -> dict:
        """Send alert to system owner — email + SMS.

        Always called for every suspicious activity regardless of type.

        Returns:
            Dict with email_ok, sms_ok, error.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        subject = f"[VigilAI] {severity}: {activity_type} detected"

        body = (
            f"VigilAI Monitoring Report\n"
            f"{'=' * 40}\n\n"
            f"Timestamp:  {timestamp}\n"
            f"Activity:   {activity_type.upper()}\n"
            f"Severity:   {severity}\n\n"
            f"Summary:\n"
            f"{summary}\n\n"
            f"{'=' * 40}\n"
            f"VigilAI Automated Monitoring System\n"
        )

        sms_msg = (
            f"[VigilAI] {severity}: {activity_type}\n"
            f"{summary}\n"
            f"Time: {timestamp}"
        )

        email_result = SendResult(False, "No owner email configured")
        sms_result = SendResult(False, "No owner phone configured")

        if self.owner_email:
            email_result = self.send_email(self.owner_email, subject, body)

        if self.owner_phone:
            sms_result = self.send_sms(self.owner_phone, sms_msg)

        error = email_result.error if not email_result.ok else sms_result.error
        return {
            "email_ok": email_result.ok,
            "sms_ok": sms_result.ok,
            "error": error,
        }

    # ------------------------------------------------------------------ #
    #  Test: Owner (for POST /test-alert)
    # ------------------------------------------------------------------ #
    def test_owner(self, message: str) -> dict:
        """Send a test email + SMS to the owner only.

        Returns:
            Dict with email_sent, sms_sent booleans.
        """
        email_result = self.send_email(
            self.owner_email,
            "[VigilAI] TEST — System check",
            message,
        )
        sms_result = self.send_sms(
            self.owner_phone,
            f"[VigilAI TEST] {message}",
        )
        return {
            "email_sent": email_result.ok,
            "sms_sent": sms_result.ok,
        }
