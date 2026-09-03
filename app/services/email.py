import asyncio
import smtplib
from email.message import EmailMessage
from typing import Protocol


class PasswordResetSender(Protocol):
    async def send_password_reset(self, email: str, code: str) -> None: ...


class EmailDeliveryError(RuntimeError):
    pass


class SmtpPasswordResetSender:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        sender: str,
        username: str = "",
        password: str = "",
        starttls: bool = True,
    ) -> None:
        self.host = host
        self.port = port
        self.sender = sender
        self.username = username
        self.password = password
        self.starttls = starttls

    async def send_password_reset(self, email: str, code: str) -> None:
        await asyncio.to_thread(self._send_password_reset, email, code)

    def _send_password_reset(self, email: str, code: str) -> None:
        message = EmailMessage()
        message["Subject"] = "Community Network Builder password reset"
        message["From"] = self.sender
        message["To"] = email
        message.set_content(
            "Use this password-reset code within 30 minutes:\n\n"
            f"{code}\n\n"
            "Open /reset-password and paste the code into the form."
        )

        try:
            with smtplib.SMTP(self.host, self.port, timeout=30) as smtp:
                if self.starttls:
                    smtp.starttls()
                if self.username:
                    smtp.login(self.username, self.password)
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as error:
            raise EmailDeliveryError from error


class DisabledPasswordResetSender:
    async def send_password_reset(self, email: str, code: str) -> None:
        raise EmailDeliveryError("SMTP is disabled")
