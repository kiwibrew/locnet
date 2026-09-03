"""Internal authorization endpoint for the database-editor proxy route."""

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.dependencies import CurrentSessionUser, get_current_admin_user
from app.security import require_same_origin

router = APIRouter()
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@router.api_route(
    "/_internal/database-authorize",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    include_in_schema=False,
)
async def authorize_database_editor(
    request: Request,
    current_user: CurrentSessionUser,
) -> Response:
    """Authorize nginx auth_request calls for every sqlite-web resource."""
    if request.headers.get("x-database-auth-request") != "1":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if not request.headers.get("x-original-uri", "").startswith("/admin/database/"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if current_user is None:
        # nginx converts this to a 303 to the sign-in page for the public route.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    await get_current_admin_user(current_user)
    if (
        request.headers.get("x-original-method", request.method).upper()
        in UNSAFE_METHODS
    ):
        require_same_origin(request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
