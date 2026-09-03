from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.repositories import UserRepository
from app.services.users import UserService


async def login(client: AsyncClient, email: str, password: str):
    page = await client.get("/")
    return await client.post(
        "/login",
        data={
            "email": email,
            "password": password,
            "csrf_token": page.cookies[settings.csrf_cookie_name],
        },
    )


async def test_administrator_manages_users_and_api_access(
    client: AsyncClient,
    database_session: AsyncSession,
):
    service = UserService(UserRepository(database_session))
    administrator = await service.create_user(
        "admin@example.com",
        "administrator password",
        is_admin=True,
    )
    user = await service.create_user(
        "person@example.com",
        "normal user password",
    )
    await login(client, administrator.email, "administrator password")

    management = await client.get("/manage-users")
    assert management.status_code == 200
    assert administrator.email in management.text
    assert user.email in management.text
    assert "password_hash" not in management.text

    enabled = await client.post(
        f"/users/{user.id}/enable-api",
        data={"csrf_token": client.cookies[settings.csrf_cookie_name]},
    )
    assert enabled.status_code == 200
    assert "Copy this token now" in enabled.text
    assert user.bearer_token_hash not in enabled.text

    disabled = await client.post(
        f"/users/{user.id}/disable-api",
        data={"csrf_token": client.cookies[settings.csrf_cookie_name]},
    )
    assert disabled.status_code == 303
    assert not user.api_access_enabled
    assert user.bearer_token_hash is None


async def test_normal_user_cannot_call_administrator_routes(
    client: AsyncClient,
    database_session: AsyncSession,
):
    user = await UserService(UserRepository(database_session)).create_user(
        "person@example.com",
        "normal user password",
    )
    await login(client, user.email, "normal user password")

    response = await client.post(
        "/users/create",
        data={
            "email": "blocked@example.com",
            "password": "blocked user password",
            "csrf_token": client.cookies[settings.csrf_cookie_name],
        },
    )
    assert response.status_code == 403
