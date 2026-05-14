from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from .firebase import verify_id_token


@dataclass(frozen=True)
class CurrentUser:
    uid: str
    email: str | None


async def get_current_user(request: Request) -> CurrentUser:
    header = request.headers.get("authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = header.removeprefix("Bearer ").strip()
    try:
        claims = verify_id_token(token)
    except Exception as exc:  # noqa: BLE001 — firebase_admin raises many subtypes
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc
    return CurrentUser(uid=str(claims["uid"]), email=claims.get("email"))  # type: ignore[arg-type]


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
