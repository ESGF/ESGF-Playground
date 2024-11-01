import os
from typing import Optional

import jwt
from dotenv import find_dotenv, load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer
from pydantic import BaseModel

ENV_FILE = find_dotenv()

load_dotenv(ENV_FILE)


PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA60CVmUcJJ7MoiuihlrSw7+BkhQbQv3HDqveFnjy2OFhKckLFyzczxCjoWq96nGTlrfWz2U4J+e8u0iHEmVaSfVDD5AG02UGNEk9TfMLuaONZjeM2w4OHYzFNaPxEmobthOcJHAsrpRwT3w4JHLEYSFVRQG8HdKha9e9qUublJVwsxFqVgPPgPK0PJpy9MSc48EMp4GbGBx9Hit9tFEIS9VPZ8BVPVm04bxOdXky/aFLsUOTS2V2FY98ABMQ8TKnbZBdXAFUnk0L3TZfkmNnvfKvUJzes79846MZKF4gVEJJ8vnD9a+u4IaMSecFCF17SEB50QMoawn3GXCK3ppZE1QIDAQAB
-----END PUBLIC KEY-----"""

TOKEN_URL = os.getenv("TOKEN_URL")

if not TOKEN_URL:
    raise Exception("TOKEN_URL is not set")


class TokenData(BaseModel):
    username: Optional[str] = None
    roles: Optional[list[str]] = []


oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="http://localhost:8086/realms/ESGF-Playground/protocol/openid-connect/auth",
    tokenUrl=TOKEN_URL,
)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:

    try:
        payload = jwt.decode(
            token,
            PUBLIC_KEY,
            algorithms=["RS256"],
            audience="ec404039-07b4-4a4f-97eb-e0accf60ee76",
        )
        username: str = payload.get("preferred_username")
        roles: list[str] = payload.get("realm_access", {}).get("roles", [])
        token_data = TokenData(username=username, roles=roles)

    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Error decoding token")

    return token_data


def get_current_active_user(
    current_user: TokenData = Depends(get_current_user),
) -> TokenData:
    if "USER" not in (current_user.roles or []) and "ADMIN" not in (
        current_user.roles or []
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user


def get_current_active_admin(
    current_user: TokenData = Depends(get_current_user),
) -> TokenData:
    if "ADMIN" not in (current_user.roles or []):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user
