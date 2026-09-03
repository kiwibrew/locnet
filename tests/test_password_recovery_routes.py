from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_password_reset_sender
from app.repositories import UserRepository
from app.services.users import UserService


class RecordingPasswordResetSender:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    async def send_password_reset(self, email: str, code: str) -> None:
        self.messages.append((email, code))


async def request_reset(client: AsyncClient, email: str):
    page = await client.get("/forgot-password")
    return await client.post(
        "/forgot-password",
        data={
            "email": email,
            "csrf_token": page.cookies[settings.csrf_cookie_name],
        },
    )


async def test_password_reset_is_private_single_use_and_changes_the_password(
    application,
    client: AsyncClient,
    database_session: AsyncSession,
):
    service = UserService(UserRepository(database_session))
    user = await service.create_user(
        "person@example.com",
        "correct horse battery staple",
    )
    sender = RecordingPasswordResetSender()
    application.dependency_overrides[get_password_reset_sender] = lambda: sender

    response = await request_reset(client, user.email)

    assert response.status_code == 200
    assert "If the account is eligible" in response.text
    assert len(sender.messages) == 1
    _, code = sender.messages[0]
    assert user.reset_token_hash == service.token_hash(code)
    assert code != user.reset_token_hash
    assert user.reset_token_expires_at.replace(tzinfo=UTC) > datetime.now(UTC)

    reset_page = await client.get("/reset-password")
    reset = await client.post(
        "/reset-password",
        data={
            "code": code,
            "password": "a different good password",
            "csrf_token": reset_page.cookies[settings.csrf_cookie_name],
        },
    )
    assert reset.status_code == 303
    assert reset.headers["location"] == "/?reset=complete"
    await service.authenticate_password(user.email, "a different good password")

    second_page = await client.get("/reset-password")
    reused = await client.post(
        "/reset-password",
        data={
            "code": code,
            "password": "yet another good password",
            "csrf_token": second_page.cookies[settings.csrf_cookie_name],
        },
    )
    assert reused.status_code == 400


async def test_unknown_and_inactive_accounts_show_the_same_acknowledgement(
    application,
    client: AsyncClient,
    database_session: AsyncSession,
):
    service = UserService(UserRepository(database_session))
    inactive = await service.create_user(
        "inactive@example.com",
        "correct horse battery staple",
    )
    inactive.is_active = False
    sender = RecordingPasswordResetSender()
    application.dependency_overrides[get_password_reset_sender] = lambda: sender

    unknown = await request_reset(client, "unknown@example.com")
    inactive_response = await request_reset(client, inactive.email)

    assert unknown.status_code == inactive_response.status_code == 200
    assert "If the account is eligible" in unknown.text
    assert "If the account is eligible" in inactive_response.text
    assert sender.messages == []
