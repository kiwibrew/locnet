from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.repositories import UserRepository
from app.services.users import UserService
from database_admin.locnet_sqlite_web import _authorize

AUTH_PATH = "/_internal/database-authorize"
PROXY_HEADERS = {
    "X-Database-Auth-Request": "1",
    "X-Original-URI": "/admin/database/defaults/content/",
    "X-Original-Method": "GET",
}


async def _sign_in(client: AsyncClient, email: str, password: str) -> None:
    page = await client.get("/")
    response = await client.post(
        "/login",
        data={
            "email": email,
            "password": password,
            "csrf_token": page.cookies[settings.csrf_cookie_name],
        },
    )
    assert response.status_code == 303


async def test_database_editor_authorizes_an_administrator_session(
    client: AsyncClient, database_session: AsyncSession
):
    await UserService(UserRepository(database_session)).create_user(
        "admin@example.com", "administrator password", is_admin=True
    )
    await _sign_in(client, "admin@example.com", "administrator password")

    response = await client.get(AUTH_PATH, headers=PROXY_HEADERS)

    assert response.status_code == 204


async def test_database_editor_rejects_anonymous_and_non_administrator_sessions(
    client: AsyncClient, database_session: AsyncSession
):
    anonymous = await client.get(AUTH_PATH, headers=PROXY_HEADERS)
    assert anonymous.status_code == 401

    await UserService(UserRepository(database_session)).create_user(
        "person@example.com", "normal user password"
    )
    await _sign_in(client, "person@example.com", "normal user password")
    non_administrator = await client.get(AUTH_PATH, headers=PROXY_HEADERS)
    assert non_administrator.status_code == 403


async def test_database_editor_rejects_cross_origin_mutations(
    client: AsyncClient, database_session: AsyncSession
):
    await UserService(UserRepository(database_session)).create_user(
        "admin@example.com", "administrator password", is_admin=True
    )
    await _sign_in(client, "admin@example.com", "administrator password")

    headers = {
        **PROXY_HEADERS,
        "X-Original-Method": "POST",
        "Origin": "https://attacker.example",
        "X-Forwarded-Host": "test",
        "X-Forwarded-Proto": "http",
    }
    assert (await client.post(AUTH_PATH, headers=headers)).status_code == 403

    headers["Origin"] = "http://test"
    assert (await client.post(AUTH_PATH, headers=headers)).status_code == 204

    headers.pop("Origin")
    headers["X-Forwarded-Host"] = "test:8000"
    headers["Referer"] = "http://test:8000/admin/database/Text/update/NA==/"
    assert (await client.post(AUTH_PATH, headers=headers)).status_code == 204


async def test_database_authorization_endpoint_is_not_a_public_route(
    client: AsyncClient,
):
    assert (await client.get(AUTH_PATH)).status_code == 404


def test_sqlite_web_authorizer_allows_application_data_but_not_credentials_or_ddl():
    import sqlite3

    assert _authorize(sqlite3.SQLITE_READ, "defaults", "value") == sqlite3.SQLITE_OK
    assert _authorize(sqlite3.SQLITE_UPDATE, "defaults", "value") == sqlite3.SQLITE_OK
    assert (
        _authorize(sqlite3.SQLITE_READ, "users", "password_hash") == sqlite3.SQLITE_DENY
    )
    assert _authorize(sqlite3.SQLITE_CREATE_TABLE, "other", None) == sqlite3.SQLITE_DENY
    assert (
        _authorize(sqlite3.SQLITE_CREATE_VTABLE, "other", None) == sqlite3.SQLITE_DENY
    )
    assert (
        _authorize(sqlite3.SQLITE_ALTER_TABLE, "main", "defaults")
        == sqlite3.SQLITE_DENY
    )
