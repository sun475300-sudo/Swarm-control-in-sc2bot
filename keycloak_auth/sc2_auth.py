"""
Phase 481: Keycloak Identity & Access Management for SC2 Bot Portal
python-keycloak client: token exchange, user management
Roles: admin, player, spectator
"""

from keycloak import KeycloakOpenID, KeycloakAdmin
from keycloak.exceptions import KeycloakAuthenticationError, KeycloakGetError
import jwt
import logging
from functools import wraps
from typing import Optional, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Keycloak configuration
KEYCLOAK_SERVER_URL = "https://auth.sc2bot.local/auth/"
REALM_NAME = "sc2bot"
CLIENT_ID = "sc2-portal"
CLIENT_SECRET = "sc2-portal-secret"

# Roles
ROLE_ADMIN = "admin"
ROLE_PLAYER = "player"
ROLE_SPECTATOR = "spectator"

keycloak_openid = KeycloakOpenID(
    server_url=KEYCLOAK_SERVER_URL,
    client_id=CLIENT_ID,
    realm_name=REALM_NAME,
    client_secret_key=CLIENT_SECRET,
    verify=True,
)

keycloak_admin = KeycloakAdmin(
    server_url=KEYCLOAK_SERVER_URL,
    username="admin",
    password="admin-password",
    realm_name=REALM_NAME,
    verify=True,
)


def get_token(username: str, password: str) -> dict:
    """Authenticate user and return tokens."""
    try:
        token = keycloak_openid.token(username, password)
        logger.info(f"Token issued for user: {username}")
        return token
    except KeycloakAuthenticationError as e:
        logger.error(f"Authentication failed for {username}: {e}")
        raise


def refresh_token(refresh_tok: str) -> dict:
    """Refresh access token using refresh token."""
    return keycloak_openid.refresh_token(refresh_tok)


def validate_token(token: str) -> dict:
    """Validate JWT token and return decoded payload."""
    try:
        public_key = keycloak_openid.public_key()
        pem_key = f"-----BEGIN PUBLIC KEY-----\n{public_key}\n-----END PUBLIC KEY-----"
        options = {"verify_signature": True, "verify_aud": True, "verify_exp": True}
        decoded = keycloak_openid.decode_token(token, key=pem_key, options=options)
        return decoded
    except Exception as e:
        logger.error(f"Token validation failed: {e}")
        raise


def get_user_roles(token: str) -> List[str]:
    """Extract roles from token payload."""
    payload = validate_token(token)
    realm_roles = payload.get("realm_access", {}).get("roles", [])
    return realm_roles


def require_role(role: str):
    """Decorator to enforce role-based access control."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, token: str = None, **kwargs):
            if not token:
                raise PermissionError("No token provided")
            roles = get_user_roles(token)
            if role not in roles:
                raise PermissionError(f"Role '{role}' required, user has: {roles}")
            return func(*args, token=token, **kwargs)
        return wrapper
    return decorator


def create_user(username: str, email: str, role: str = ROLE_PLAYER) -> str:
    """Create a new SC2 bot portal user."""
    user_id = keycloak_admin.create_user({
        "username": username,
        "email": email,
        "enabled": True,
        "emailVerified": True,
    })
    role_obj = keycloak_admin.get_realm_role(role)
    keycloak_admin.assign_realm_roles(user_id, [role_obj])
    logger.info(f"Created user {username} with role {role}")
    return user_id


def token_exchange(subject_token: str, target_client: str) -> dict:
    """Exchange token for another service (token exchange flow)."""
    return keycloak_openid.exchange_token(
        token=subject_token,
        audience=target_client,
    )


@require_role(ROLE_ADMIN)
def admin_action(token: str = None, action: str = ""):
    """Example admin-only action."""
    logger.info(f"Admin action performed: {action}")
    return {"status": "ok", "action": action}
