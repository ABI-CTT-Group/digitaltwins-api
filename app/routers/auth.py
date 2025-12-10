"""
IAM by Keycloak
"""
import requests
import os

from fastapi import APIRouter
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from dotenv import load_dotenv

router = APIRouter()

load_dotenv()
# Keycloak configs
KEYCLOAK_BASE_URL = os.getenv("KEYCLOAK_BASE_URL")
REALM = os.getenv("REALM")
ALGORITHM = os.getenv("ALGORITHM")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REALM_URL = os.getenv("CLIENT_SECRET")
KEYCLOAK_TOKEN_URL = os.getenv("KEYCLOAK_TOKEN_URL")
KEYCLOAK_INTROSPECT_URL = os.getenv("KEYCLOAK_INTROSPECT_URL")


def auth_basic(credentials: HTTPBasicCredentials = Depends(HTTPBasic())):
    result = get_token(credentials)
    if not result.get("access_token"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    else:
        return True


def auth_bearer(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    token = credentials.credentials
    data = {
        "token": token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    # verify token by introspection
    r = requests.post(KEYCLOAK_INTROSPECT_URL, data=data)
    result = r.json()
    if not result.get("active", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    else:
        return True


def validate_credentials(
        basic_credentials: HTTPBasicCredentials = Depends(HTTPBasic(auto_error=False)),
        bearer_credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
):
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
    result = get_token(credentials)
    return result


@router.post("/token", tags=["auth"])
def get_token(
        basic_credentials: HTTPBasicCredentials = Depends(HTTPBasic(auto_error=False)),
        bearer_credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
):
    if basic_credentials:
        payload = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "password",
            "username": basic_credentials.username,
            "password": basic_credentials.password
        }
    elif bearer_credentials:
        payload = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": bearer_credentials.credentials
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication method",
            headers={"WWW-Authenticate": "Basic, Bearer"},
        )

    response = requests.post(KEYCLOAK_TOKEN_URL, data=payload)

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    response_json = response.json()
    # token = response_json.get("access_token")

    return response.json()


@router.get("/verify_token", tags=["auth"])
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    return {"active": auth_bearer(credentials)}
