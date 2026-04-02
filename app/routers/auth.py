"""
IAM by Keycloak
"""
import requests
import os

from fastapi import APIRouter
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from jose import jwt as jose_jwt, JWTError

from dotenv import load_dotenv

router = APIRouter()

load_dotenv()
# Keycloak configs
KEYCLOAK_BASE_URL = os.getenv("KEYCLOAK_BASE_URL")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM")
KEYCLOAK_ALGORITHM = os.getenv("KEYCLOAK_ALGORITHM")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET")

keycloak_realm_url = f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}"
keycloak_token_url = f"{keycloak_realm_url}/protocol/openid-connect/token"
keycloak_introspect_url = f"{keycloak_token_url}/introspect"

# Cache the public key to avoid fetching it on every request
_cached_public_key: str | None = None


def get_keycloak_public_key() -> str:
    """Fetch and cache the Keycloak realm public key."""
    global _cached_public_key
    if _cached_public_key is None:
        r = requests.get(keycloak_realm_url, verify=False)
        r.raise_for_status()
        raw_key = r.json().get("public_key")
        _cached_public_key = f"-----BEGIN PUBLIC KEY-----\n{raw_key}\n-----END PUBLIC KEY-----"
    return _cached_public_key


def auth_basic(credentials: HTTPBasicCredentials = Depends(HTTPBasic())):
    result = get_token(credentials)
    if not result.get("access_token"):
        print(f"[auth] Basic auth failed, Keycloak response: {result}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result
        )
    else:
        return True


def auth_bearer(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    token = credentials.credentials
    # Verify the JWT locally using the Keycloak realm public key.
    # Introspection is intentionally avoided here: the frontend issues tokens via the
    # public client "portal-frontend", whose tokens don't include the "api" client in
    # their audience.  Keycloak therefore rejects introspection requests from the "api"
    # confidential client with INTROSPECT_TOKEN_ERROR / invalid_token.
    # Local verification works for any token issued by this Keycloak realm, regardless
    # of which client originally issued it.
    try:
        public_key_pem = get_keycloak_public_key()
        jose_jwt.decode(
            token,
            public_key_pem,
            algorithms=[KEYCLOAK_ALGORITHM],
            options={"verify_aud": False},
        )
        return True
    except JWTError as e:
        # Public key may have rotated — clear cache and retry once
        global _cached_public_key
        _cached_public_key = None
        print(f"[auth] Bearer token verification failed (will retry with fresh key): {e}")
        try:
            public_key_pem = get_keycloak_public_key()
            jose_jwt.decode(
                token,
                public_key_pem,
                algorithms=[KEYCLOAK_ALGORITHM],
                options={"verify_aud": False},
            )
            return True
        except JWTError as e2:
            print(f"[auth] Bearer token verification failed: {e2}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e2),
            )
    except Exception as e:
        print(f"[auth] Bearer token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


def validate_credentials(
        basic_credentials: HTTPBasicCredentials = Depends(HTTPBasic(auto_error=False)),
        bearer_credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
):
    print(f"basic_credentials: {basic_credentials}")
    print(f"bearer_credentials: {bearer_credentials}")
    if basic_credentials:
        valid = auth_basic(basic_credentials)
        return valid
    elif bearer_credentials:
        valid = auth_bearer(bearer_credentials)
        return valid
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication method",
            headers={"WWW-Authenticate": "Basic or Bearer"},
        )


@router.post("/login", tags=["auth"])
def login(credentials: HTTPBasicCredentials = Depends(HTTPBasic())):
    # validate_credentials(credentials)
    result = get_token(basic_credentials=credentials)
    return result


@router.post("/token", tags=["auth"])
def get_token(
        basic_credentials: HTTPBasicCredentials = Depends(HTTPBasic(auto_error=False)),
        bearer_credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
):
    if basic_credentials:
        payload = {
            "client_id": KEYCLOAK_CLIENT_ID,
            "client_secret": KEYCLOAK_CLIENT_SECRET,
            "grant_type": "password",
            "username": basic_credentials.username,
            "password": basic_credentials.password
        }
    elif bearer_credentials:
        payload = {
            "client_id": KEYCLOAK_CLIENT_ID,
            "client_secret": KEYCLOAK_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": bearer_credentials.credentials
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication method",
            headers={"WWW-Authenticate": "Basic, Bearer"},
        )

    response = requests.post(keycloak_token_url, data=payload)

    if response.status_code != 200:
        try:
            error_detail = response.json()
        except ValueError:
            error_detail = response.text
        print(f"[auth] Keycloak token error ({response.status_code}): {error_detail}")
        raise HTTPException(status_code=response.status_code, detail=error_detail)

    response_json = response.json()
    # token = response_json.get("access_token")

    return response.json()


@router.get("/verify_token", tags=["auth"])
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    return {"active": auth_bearer(credentials)}
