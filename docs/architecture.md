# Application Architecture Standard

This document defines the architecture for this Application.

`Must` states a requirement. `Should` states the normal design unless a documented constraint prevents it.

## Execution environment

Docker Compose is the only supported application environment.

* The `Dockerfile` must use `FROM python:3.14-slim` as its base image.
* Development, test, and production images must use CPython 3.14.
* Develop, run, test, lint, format, type-check, and migrate the application through Docker Compose.
* Do not run Python, Uvicorn, pytest, Alembic, Ruff, mypy, or a package manager on the host.
* Do not create a host-side virtual environment.
* Declare every dependency in the repository and install it in the application image.
* Use `docker compose run --rm web-locnet ...` for a one-time application command.
* Use `docker compose exec web-locnet ...` only when the `web-locnet` service is already running.
* Use host tools only for file editing, Git, Docker, and Docker Compose.
* Bind-mount directories that must keep container-generated files.
* Do not fix a missing container dependency with a host installation.
* The project must run on a clean host with Git, Docker Engine, and Docker Compose.

The primary application service name is `web-locnet`. Supporting services may provide the Node.js and Playwright toolchains.

### Standard commands

```bash
docker compose up --build
docker compose down
docker compose run --rm test pytest
docker compose run --rm test pytest --cov=app
docker compose run --rm web-locnet ruff check .
docker compose run --rm web-locnet ruff format --check .
docker compose run --rm web-locnet mypy app/
docker compose run --rm spa npm ci
docker compose run --rm spa npm test
docker compose run --rm spa npm run build
docker compose run --rm playwright npm ci
docker compose run --rm playwright npm test
```

The Compose configuration must publish the application port. Uvicorn must listen on `0.0.0.0` inside the container.
Do not commit `docker-compose.yml` or `.env`. Commit `docker-compose.yml.example`, `.env.example`, `Dockerfile`, and `.dockerignore`.

## Core architecture

* Framework: FastAPI with `async` and `await` throughout.
* Python: CPython 3.14 from the `python:3.14-slim` image.
* Validation: Pydantic v2 request and response schemas.
* Authentication: browser-session JWTs through `python-jose`, optional persistent API tokens, and a configured password-hashing adapter.
* Testing: pytest with `httpx.AsyncClient` and ASGI transport.
* Browser testing: Playwright against the production-built application.

* Runtime: Docker Compose only.

### Project structure

```text
app/
├── main.py              # App factory, lifespan, middleware, exception handlers
├── config.py            # Environment-backed Pydantic settings
├── database.py          # Async engine, session factory, request transaction
├── dependencies.py      # Database, authentication, and service dependencies
├── models/              # SQLAlchemy models
├── schemas/             # Pydantic request and response schemas
├── routers/             # API and UI routes, split by domain
├── services/            # Business rules and lifecycle operations
├── repositories/        # Database queries and persistence operations
└── templates/           # Jinja base and authentication page templates
spa/                      # React and TypeScript single-page application
├── src/                  # Components, features, API client, and unit tests
├── package.json          # Exact frontend dependency versions and commands
└── package-lock.json     # Reproducible npm dependency graph
tests/
├── conftest.py          # Client, database, authentication, and factory fixtures
├── test_routers/        # API and UI integration tests
└── test_services/       # Business-rule unit tests
migrations/              # Alembic environment and revisions
playwright/
├── tests/                # Browser end-to-end tests
├── playwright.config.ts  # Browser and artifact configuration
├── package.json          # Exact Playwright and TypeScript versions
└── package-lock.json     # Reproducible npm dependency graph
```

### Frontend environment

* Node.js 24 LTS is the supported runtime. Node.js must satisfy `>=24 <25`.
* React and React DOM must be version 19.2 or newer within major version 19 and must use identical versions.
* TypeScript must be version 5.9 or newer within major version 5.
* Vite must be version 8.1 or newer within major version 8.
* TypeScript application and Playwright code must pass strict type checking.
* Package manifests must pin exact dependency versions and commit npm lockfiles.
* Automated and container builds must install packages with `npm ci`.
* The SPA and Playwright packages must declare the supported Node.js engine and reject an incompatible engine.
* A major-version upgrade requires an update to this standard and a passing backend, frontend, and Playwright test suite.

The current approved patch versions are React and React DOM 19.2.8, TypeScript 5.9.3, Vite 8.1.5, and Playwright 1.61.1.

### Layer rules

* Routers parse HTTP input and apply dependencies.
* Routers call services. They must not contain business rules or database queries.
* Services own normalization, authorization-independent business rules, and state transitions.
* Use dependency injection for sessions and services.
* Do not use global mutable state.
* Do not use synchronous database drivers or blocking I/O in an async route.
* Move necessary blocking file work to a thread with `asyncio.to_thread`.
* The SPA is the authenticated application UI and is served from `/app`.
* The SPA calls same-origin `/api` routes with the browser-session cookie.
* The SPA must not read or store the session JWT or a persistent API token.
* Client-side visibility rules improve usability but never replace server-side authorization.

API routes must return typed Pydantic response models. UI routes must declare `HTMLResponse` or `RedirectResponse`.
Create separate Pydantic models for create, update, public response, and credential response data.
Never return a raw ORM model or an untyped dictionary from an API route.

### Configuration and secrets

* Read configuration with `pydantic-settings`.
* Supply deployment values through environment variables, Compose environment files, or Docker secrets.
* Do not bake a secret into an image.
* Do not hardcode a production credential or database path.
* Containers must use Compose service names for network connections. They must not use `localhost` for another container.

### Local SQLite data

* SQLite is the application database. The application must not depend on Grist or another remote data API for its reference data.
* Use SQLAlchemy's async engine and `aiosqlite` for all request-time database access.
* The request-scoped session must commit one successful transaction and roll back a failed transaction.
* Repositories own SQL queries and persistence operations. Services and routers must not construct SQL.
* Every value supplied by a user or external system must be passed to SQLAlchemy as a bound parameter.
* Create and change application-owned tables only through Alembic migrations.
* Store the runtime database in a bind-mounted data directory and do not commit it.
* If the application distributes reference data in SQLite form, commit it as a separate immutable seed database. Initialise a new runtime database from that seed and then apply migrations.
* Authentication records, API token digests, password-reset state, and mutable caches belong only in the runtime database.

### Error handling

* Let Pydantic return its standard HTTP 422 validation response.
* Raise domain exceptions from services.
* Keep domain exceptions independent of FastAPI.
* Register domain-to-HTTP mappings in `main.py`.
* Use `HTTPException` for HTTP-specific client errors.
* Catch only an exception that the code can recover from or translate.
* Let unexpected exceptions reach the central error handler.
* Log enough context to diagnose an unexpected error.
* Never log a password, password hash, session JWT, persistent token, or secret.

### Route contract

| Method | Path | Access | Result |
| --- | --- | --- | --- |
| `GET` | `/` | Public | Sign-in page, or redirect an authenticated user to `/app`. |
| `GET` | `/health` | Public | Container health status. |
| `GET` | `/static/*`, `/assets/*`, `/documentation-assets/*` | Public | Static application assets. |
| `GET` | `/app` | Session user | React single-page application. |
| `GET` | `/app/{path}` | Session user | React client-side route fallback when client-side routing is used. |
| `POST` | `/login` | Public | Browser-session creation and redirect to `/app`. |
| `POST` | `/logout` | Session user | Session deletion and redirect to `/`. |
| `GET` | `/forgot-password` | Public | Password-reset request page. |
| `POST` | `/forgot-password` | Public | Create and email a password-reset code when the account is eligible. |
| `GET` | `/reset-password` | Public | Form for a reset code and new password. |
| `POST` | `/reset-password` | Public reset code | Consume the code and replace the password. |
| `GET` | `/documentation` | Public | Application documentation. |
| `GET` | `/qsg` | Public | Quick-start guide. |
| `GET` | `/faq` | Public | Frequently asked questions. |
| `GET` | `/docs` | API-enabled normal session user | Authenticated Swagger UI. |
| `GET` | `/openapi.json` | API-enabled normal session user | Protected OpenAPI document. |
| `GET` | `/manage-users` | Active user | Own account or administrator account list. |
| `POST` | `/users/create` | Administrator | User creation. |
| `POST` | `/users/{user_id}/enable-api` | Administrator | Enable API access and issue the first persistent token. |
| `POST` | `/users/{user_id}/disable-api` | Administrator | Disable API access and revoke the persistent token. |
| `POST` | `/users/{user_id}/regen-token` | Administrator | Replace the persistent token of an API-enabled user. |
| `POST` | `/users/{user_id}/toggle-active` | Administrator | Account activation or deactivation. |
| `POST` | `/users/{user_id}/toggle-admin` | Administrator | Role change. |
| `POST` | `/users/{user_id}/delete` | Administrator | User deletion. |
| Any | `/admin/database/*` | Administrator session | Reverse-proxied sqlite-web editor for allowlisted application-data tables. |
| Any | `/api/*` | Active session user or active API-enabled normal user's persistent token | Application API response. |

Application API routes must use an `/api` prefix. Use `/api/v1` when external clients need a stable version.

Session-cookie access to `/api/*` exists for the first-party SPA and is available to every active signed-in user. Direct API access uses `Authorization: Bearer TOKEN` and is available only to an active, non-administrator user whose API access is enabled. A server cannot prove that a cookie-authenticated request was initiated by the React code, so this credential boundary is the enforceable distinction.

### Page behavior

* The public home page must show an email and password form.
* The sign-in form must link to `/forgot-password`.
* A successful sign-in must redirect to `/app` with HTTP 303.
* An anonymous request for `/app` must redirect to `/` with HTTP 303.
* The SPA must identify the current user and provide a Sign out control.
* Show the Swagger link only to an API-enabled normal user.
* Show a safe error for invalid credentials or an inactive account.
* Do not expose whether an unknown email exists.
* A password-reset request must always show the same acknowledgement, including for an
  unknown, inactive, or undeliverable email address.
* Use `POST` for every state change.
* Return HTTP 303 after a successful form submission.
* A destructive control must name the action and require confirmation.
* Do not render a control that the current user cannot use.
* Enforce the same authorization on the server.
* Use Bootstrap alerts for expected UI errors.
* Do not put credentials or internal exception details in an alert.

### Administrator database editor

`/admin/database/` is a same-origin, administrator-only sqlite-web interface.
Nginx applies an internal FastAPI `auth_request` check to every editor request,
including assets. Anonymous requests redirect to `/`; authenticated non-administrators
receive HTTP 403. Unsafe editor requests require a same-origin `Origin` or `Referer`.

The editor receives the runtime SQLite bind mount but may browse and edit only its
explicit allowlist of application-data tables. Authentication tables and credentials
are never exposed. The sqlite-web wrapper blocks query, schema, index, trigger,
attach, detach, and other DDL operations at both route and SQLite-authorizer levels.
Schema changes remain Alembic-only.

### Authenticated API documentation

* Disable FastAPI's default public Swagger, ReDoc, and OpenAPI routes.
* Supply protected `/docs` and `/openapi.json` routes for API-enabled normal users.
* Redirect an anonymous `/docs` request to `/` with HTTP 303.
* Return HTTP 401 for an anonymous `/openapi.json` request.
* Return HTTP 403 when an authenticated administrator or an API-disabled user requests either resource.
* Add the common application navigation to Swagger.

### Browser security

* Store the session JWT in an HTTP-only cookie.
* Set `SameSite=Lax`, `Path=/`, and an explicit maximum age.
* Configure the cookie `Secure` flag from the environment.
* Production HTTPS deployments must enable the `Secure` flag.
* Delete the cookie with the same path and attributes used to create it.
* Protect cookie-authenticated state changes from cross-site request forgery (CSRF).
* Use a CSRF token or strict Origin and Referer validation.
* Do not put a session JWT, persistent token, reset code, password, or password hash in a URL.
* Submit a reset code only in the body of the password-reset form.

## API user-management standard

### User data model

| Field | Requirement |
| --- | --- |
| `id` | Integer primary key. |
| `email` | Lowercase email, maximum 320 characters, unique index. |
| `password_hash` | Password hash only. |
| `api_access_enabled` | Non-null feature flag. New users start with API access disabled. |
| `bearer_token_hash` | Nullable, unique, indexed SHA-256 digest of the current persistent API token. |
| `is_active` | Non-null status flag. New users start active. |
| `is_admin` | Non-null role flag. |
| `created_at` | Non-null UTC creation time. |
| `last_login_at` | Nullable UTC time of the last successful sign-in. |
| `reset_token_hash` | Nullable, indexed SHA-256 digest of the current password-reset code. |
| `reset_token_expires_at` | Nullable UTC expiry time for the current password-reset code. |

Create and change the user table only through Alembic migrations.

### Roles and visibility

* An administrator manages users with an email, password, and browser-session JWT.
* Every active user accesses the SPA and its same-origin API calls with a browser-session JWT.
* An API-enabled normal user can also access protected API routes with one persistent bearer token.
* API access is disabled by default and an administrator turns it on or off through user management.
* An administrator must not have API access enabled or a persistent bearer token.
* An administrator can see all accounts on `/manage-users`.
* A non-administrator can see only their account.
* Show a new persistent token once, immediately after enablement or regeneration. Do not store or redisplay the plain token.
* The enable and regeneration routes may return a no-store credential page instead of an HTTP 303 redirect.
* Show API enablement status, but never a token digest, in user management.
* Never show a password hash in HTML, JSON, logs, errors, or API documentation.
* Exclude credentials from general response schemas.
* Use a dedicated credential response when a route must return a token.

### Identity and password rules

* Validate each email with Pydantic `EmailStr`.
* Convert the email to lowercase before each lookup or write.
* Enforce email uniqueness in both the service and database.
* Validate passwords on the server with a length from 8 through 128 characters.
* Hash a new password with the configured modern password hasher.
* Prefer Argon2 for new hashes and support bcrypt verification for legacy hashes.
* Never store or log a password.

### Password recovery

The password-recovery flow follows the `kiwibrew/mcc_id` design. A user submits an email address.
The service creates a random code and emails it to the user. The user pastes the code and a new
password into the password-reset form.

* Generate a reset code with `secrets.token_urlsafe(48)`. Never store the plain code.
* Store the SHA-256 digest of the code in an indexed database column.
* Expire the code 30 minutes after the service issues it.
* Issue a code only for an active account, but return the same public acknowledgement for every
  syntactically valid email address.
* A new reset request must replace any prior reset code for that account.
* Email the code as plain text. Tell the user to open `/reset-password` and paste the code.
* Do not put the code or the email address in the reset-page URL.
* Send the email through the configured SMTP service without blocking the async event loop.
* If delivery fails, clear the unsent code state, log the failure without credentials, and return
  the same public acknowledgement.
* Hash a submitted code with SHA-256 and find the account by the stored digest.
* Validate the account status and UTC expiry before changing a password.
* Apply the normal 8-through-128-character password validation to the new password.
* After a successful reset, replace the password hash and clear both reset-code fields in the same
  transaction. Thus, the user cannot use the code again.
* Return HTTP 400 with a generic invalid-code error for every failed code validation.
* Redirect a successful reset to `/` with HTTP 303 and show a confirmation on the sign-in page.
* Read SMTP enablement, host, port, and sender address from settings.

### Credential rules

The service uses two credential types:

1. A signed JWT in an HTTP-only cookie authenticates a browser session.
2. A random persistent token authenticates an API-enabled normal user through the bearer header.

The JWT must contain `sub`, `exp`, and a credential-type claim with the value `session`. The `sub` value identifies the normalized email. The application does not issue or accept short-lived bearer JWTs.

Generate each persistent token with at least 256 bits of secure random input. `secrets.token_urlsafe(32)` is the reference generator. Store only the SHA-256 digest of the token.

* UI routes authenticate only with the session cookie.
* API routes read `Authorization: Bearer TOKEN` when that header is present and must not fall back to the session cookie after an invalid bearer credential.
* Resolve a bearer token by hashing it and finding an active, API-enabled, non-administrator user through the unique digest.
* When an API request has no bearer header, authenticate it with the browser-session cookie for use by the SPA.
* Never decode a bearer-header value as a JWT.
* Accept only the configured JWT algorithm for the session cookie.
* Reject an invalid, expired, or incorrectly typed session JWT.
* Check `is_active` on every authenticated request.
* Update `last_login_at` only after successful password authentication.
* Never log a full JWT or persistent token.

### Authorization dependencies

Define these reusable dependencies in `app/dependencies.py`:

* `get_current_session_user` resolves the session cookie and can return no user.
* `get_current_active_session_user` requires an authenticated and active browser-session user.
* `get_current_api_principal` resolves a persistent bearer token when present or otherwise requires an active browser-session user.
* `get_current_api_enabled_session_user` requires an active, non-administrator session user with API access enabled; use it for Swagger and OpenAPI.
* `get_current_admin_user` requires an active administrator session.
* `get_user_service` creates a service with the request repository and session.

An anonymous API request must return HTTP 401 and `WWW-Authenticate: Bearer`.
An anonymous UI request must redirect to `/`. A disabled or unauthorized account must receive HTTP 403.

### Lifecycle rules

* Create every user with API access disabled and without a persistent token.
* Enabling API access for a normal user must generate a token, store only its digest, and return the plain token once.
* Disabling API access must clear the token digest and invalidate the token immediately.
* Token regeneration is permitted only for an API-enabled normal user and must invalidate the old token immediately.
* Do not enable API access or generate a persistent token for an administrator.
* Promotion to administrator must disable API access and remove the persistent-token digest.
* Demotion to normal user must leave API access disabled. An administrator may enable it in a separate action.
* Deactivation must stop session and persistent-token access on the next request.
* Do not let an administrator deactivate their own account.
* Do not let an administrator change their own role.
* Do not let an administrator delete their own account.
* Do not remove or deactivate the last active administrator.
* Return HTTP 404 when the target user does not exist.
* Return HTTP 409 when the email already exists.
* Return HTTP 400 for a prohibited lifecycle operation.

### User-management layers

* The router parses forms, applies dependencies, and returns a redirect.
* The user service owns email normalization, hashing, token generation, and lifecycle safeguards.
* The user repository owns user queries and persistence operations.
* A router must not access `service.repository`.
* The request transaction must commit all successful changes and roll back each failure.

### Bootstrap and operations

Supply `python -m app.admin create-admin EMAIL` to create the first administrator.
Supply `python -m app.admin remove-user EMAIL` to remove a user.

* Run the command only through `docker compose run --rm web-locnet ...`.
* Use the same service and repository layers as the web application.
* Do not print a password, password hash, JWT, or persistent token.
* Store the runtime SQLite database in a bind-mounted data directory.
* Set a long random JWT secret before a production start.

## Testing standard

Tests must use a separate database. Each pytest repository and API integration test must use an isolated transaction that rolls back. Playwright must use a disposable end-to-end database that is reset to deterministic seed data.
Mock external services, but use the real test database engine for repository and API integration tests.

The test suite must cover these cases:

* A valid sign-in sets the configured session cookie.
* Invalid credentials do not create a session.
* A password-reset request has the same response for unknown, inactive, and active accounts.
* A reset email contains a code with a 30-minute expiry while the database stores only its digest.
* A valid reset code changes the password, is single-use, and redirects with HTTP 303.
* Invalid, expired, reused, and inactive-account reset codes do not change a password.
* A second reset request invalidates the first code.
* Password-reset delivery does not block the async event loop, and delivery failure does not reveal
  whether the account exists.
* An inactive user cannot sign in or use the API.
* An active browser session can authenticate an API request made by the SPA.
* An enabled persistent token can authenticate an API request, while a disabled or replaced token cannot.
* The application does not issue or accept a short-lived bearer JWT.
* Anonymous users cannot access the SPA, Swagger, OpenAPI, or user management.
* API-disabled users and administrators cannot access Swagger or OpenAPI.
* A non-administrator sees only their account and cannot call an administrator route.
* An administrator can make each permitted lifecycle change.
* Self-protection rules reject each prohibited lifecycle change.
* The service protects the last active administrator.
* Enabling API access returns a persistent token once, and disabling access invalidates it.
* A replacement token works and the old token fails.
* Promotion disables API access, while demotion leaves API access disabled.
* User pages and API responses never contain a password hash.
* Public and authenticated UI pages use the same light application styling without a black navigation bar.
* The navigation provides the controls allowed for the current user and a CSRF-protected Sign out form.
* Swagger uses the equivalent light navigation and control layout.
* UI mutations reject requests without valid CSRF protection.
* Successful form routes return HTTP 303 and show the changed state.

Run all tests and checks through Docker Compose. The suite must run from a clean checkout without host dependencies.

### Playwright browser tests

* Playwright is the required browser end-to-end test framework.
* Run Playwright through Docker Compose against the production-built SPA and FastAPI application.
* The Playwright package and container image must use matching Playwright versions.
* Use `http://web-locnet:8000` as the default Compose-network base URL and allow an environment override.
* Wait for an application health check before the browser suite starts.
* Tests must use an isolated disposable database, deterministic seed data, and separate administrator, API-disabled user, and API-enabled user identities.
* Tests must not depend on execution order or fixed-duration sleeps.
* Prefer accessible role and label locators. Use stable test IDs when no accessible locator identifies the control.
* Use Playwright web-first assertions and observable response or UI conditions.
* Run Chromium on every change and Firefox in CI. WebKit may run as a scheduled compatibility check.
* Retain traces, screenshots, and the HTML report for failed CI tests.
* Browser tests must cover sign-in, sign-out, failed and inactive sign-in, password recovery, `/app` protection, SPA API use, Swagger and OpenAPI authorization, CSRF rejection, API enablement and revocation, role-based controls, and administrator lifecycle operations.

## Prohibited patterns

* Host-side application commands or dependencies.
* Host-side Node.js, npm, Vite, or Playwright commands or dependencies.
* Synchronous database access in an async request.
* Raw ORM objects or untyped dictionaries from API routes.
* Public Swagger or OpenAPI documents.
* UI controls without matching server authorization.
* Password hashes in a user interface or response.
* Plain persistent API tokens in the database or redisplayed after initial issue.
* Short-lived bearer JWT issue or acceptance.
* Session JWTs, persistent tokens, reset codes, reset-code digests, passwords, or secrets in logs
  and URLs.
* A committed runtime SQLite database.
* Hardcoded deployment configuration.
* Global mutable application state.
* State changes through `GET` routes.
* Manual container changes that are absent from the repository.
