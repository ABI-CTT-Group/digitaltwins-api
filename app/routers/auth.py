"""
IAM by Keycloak

This module handles identity and access management using Keycloak. It provides functions
and endpoints for user authentication, token retrieval, and token validation using both
Basic and Bearer authentication schemes.
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
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM")
KEYCLOAK_ALGORITHM = os.getenv("KEYCLOAK_ALGORITHM")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET")

keycloak_realm_url = f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}"
keycloak_token_url = f"{keycloak_realm_url}/protocol/openid-connect/token"
keycloak_introspect_url = f"{keycloak_token_url}/introspect"


def auth_basic(credentials: HTTPBasicCredentials = Depends(HTTPBasic())):
    """
    Authenticate a user using Basic Authentication.

    Args:
        credentials (HTTPBasicCredentials, optional): The base64 encoded username and password.

    Returns:
        bool: True if authentication is successful.

    Raises:
        HTTPException: If the username or password is invalid (Status 401).
    """
    result = get_token(credentials)
    if not result.get("access_token"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    else:
        return True


def auth_bearer(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """
    Authenticate a user using Bearer Token Authentication.

    Validates the bearer token by introspecting it against Keycloak.

    Args:
        credentials (HTTPAuthorizationCredentials, optional): The bearer token provided in the Authorization header.

    Returns:
        bool: True if the token is active and valid.

    Raises:
        HTTPException: If the token is invalid or inactive (Status 401).
    """
    token = credentials.credentials
    data = {
        "token": token,
        "client_id": KEYCLOAK_CLIENT_ID,
        "client_secret": KEYCLOAK_CLIENT_SECRET
    }
    # verify token by introspection
    r = requests.post(keycloak_introspect_url, data=data)
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
    """
    Validate incoming credentials, allowing either Basic or Bearer schemes.

    Args:
        basic_credentials (HTTPBasicCredentials, optional): The Basic auth credentials.
        bearer_credentials (HTTPAuthorizationCredentials, optional): The Bearer auth credentials.

    Returns:
        bool: True if either of the provided credentials is valid.

    Raises:
        HTTPException: If no valid authentication method is provided (Status 401).
    """
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
    """
    Log in a user to retrieve an access token.

    Args:
        credentials (HTTPBasicCredentials, optional): Basic auth containing username and password.

    Returns:
        dict: The Keycloak token response, usually containing an access_token.
    """
    # validate_credentials(credentials)
    result = get_token(basic_credentials=credentials)
    return result


@router.post("/token", tags=["auth"])
def get_token(
        basic_credentials: HTTPBasicCredentials = Depends(HTTPBasic(auto_error=False)),
        bearer_credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
):
    """
    Retrieve or refresh an access token from Keycloak.

    Args:
        basic_credentials (HTTPBasicCredentials, optional): Provided to retrieve a token via password grant.
        bearer_credentials (HTTPAuthorizationCredentials, optional): Provided to refresh a token via refresh_token grant.

    Returns:
        dict: The JSON representation of the token response.

    Raises:
        HTTPException: If no valid authentication method is provided or if credential validation fails (Status 401).
    """
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
        raise HTTPException(status_code=401, detail="Invalid credentials")

    response_json = response.json()
    # token = response_json.get("access_token")

    return response.json()


@router.get("/verify_token", tags=["auth"])
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """
    Verify the validity of a Bearer token.

    Args:
        credentials (HTTPAuthorizationCredentials, optional): Bearer token from the Authorization header.

    Returns:
        dict: A dictionary containing an 'active' key that is True if the token is valid.
    """
    return {"active": auth_bearer(credentials)}
