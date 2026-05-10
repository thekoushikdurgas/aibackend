"""
Supabase Authentication WebSocket Methods
"""

import logging
from typing import Any, Dict, Optional, cast

from supabase_auth.types import (
    Options,
    Provider,
    SignInWithEmailAndPasswordlessCredentials,
    SignInWithEmailAndPasswordlessCredentialsOptions,
    SignInWithOAuthCredentials,
    SignInWithOAuthCredentialsOptions,
    UserAttributes,
)

from app.core.supabase_client import get_supabase_client, is_supabase_configured
from app.core.ws_auth import require_auth
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode

logger = logging.getLogger(__name__)


async def handle_auth_signup(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """
    Handle auth.signup - Email/password registration

    Args:
        params: {
            "email": str,
            "password": str,
            "metadata": dict (optional)
        }
    """
    if not is_supabase_configured():
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, "Supabase is not configured"
        )

    email = params.get("email")
    password = params.get("password")
    metadata = params.get("metadata", {})

    if not email or not password:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Email and password are required"
        )

    try:
        supabase = get_supabase_client()
        if not supabase:
            raise JSONRPCError(
                JSONRPCErrorCode.INTERNAL_ERROR, "Failed to initialize Supabase client"
            )

        response = supabase.auth.sign_up(
            {"email": email, "password": password, "options": {"data": metadata}}
        )

        result: Dict[str, Any] = {
            "success": True,
            "user": None,
            "session": None,
            "requires_confirmation": False,
        }

        if response.user:
            result["user"] = {
                "id": response.user.id,
                "email": response.user.email,
                "user_metadata": response.user.user_metadata or {},
                "app_metadata": response.user.app_metadata or {},
                "created_at": response.user.created_at,
            }

        if response.session:
            result["session"] = {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "expires_in": response.session.expires_in,
                "expires_at": response.session.expires_at,
                "token_type": response.session.token_type,
            }
        else:
            # Email confirmation required
            result["requires_confirmation"] = True

        return result

    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise JSONRPCError(JSONRPCErrorCode.INTERNAL_ERROR, f"Signup failed: {str(e)}")


async def handle_auth_signin(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """
    Handle auth.signin - Email/password login

    Args:
        params: {
            "email": str,
            "password": str
        }
    """
    if not is_supabase_configured():
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, "Supabase is not configured"
        )

    email = params.get("email")
    password = params.get("password")

    if not email or not password:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Email and password are required"
        )

    try:
        supabase = get_supabase_client()
        if not supabase:
            raise JSONRPCError(
                JSONRPCErrorCode.INTERNAL_ERROR, "Failed to initialize Supabase client"
            )

        response = supabase.auth.sign_in_with_password(
            {"email": email, "password": password}
        )

        if not response.user or not response.session:
            raise JSONRPCError(
                JSONRPCErrorCode.AUTHENTICATION_ERROR, "Invalid email or password"
            )

        return {
            "success": True,
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "user_metadata": response.user.user_metadata or {},
                "app_metadata": response.user.app_metadata or {},
                "created_at": response.user.created_at,
            },
            "session": {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "expires_in": response.session.expires_in,
                "expires_at": response.session.expires_at,
                "token_type": response.session.token_type,
            },
        }

    except Exception as e:
        logger.error(f"Signin error: {e}")
        error_msg = str(e)
        if (
            "Invalid login credentials" in error_msg
            or "Email not confirmed" in error_msg
        ):
            raise JSONRPCError(JSONRPCErrorCode.AUTHENTICATION_ERROR, error_msg)
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Signin failed: {error_msg}"
        )


async def handle_auth_signout(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """
    Handle auth.signout - Logout and invalidate session

    Args:
        params: {} (optional)
    """
    if not is_supabase_configured():
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, "Supabase is not configured"
        )

    try:
        supabase = get_supabase_client()
        if not supabase:
            raise JSONRPCError(
                JSONRPCErrorCode.INTERNAL_ERROR, "Failed to initialize Supabase client"
            )

        # Sign out current session
        supabase.auth.sign_out()

        return {"success": True, "message": "Signed out successfully"}

    except Exception as e:
        logger.error(f"Signout error: {e}")
        raise JSONRPCError(JSONRPCErrorCode.INTERNAL_ERROR, f"Signout failed: {str(e)}")


async def handle_auth_refresh(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """
    Handle auth.refresh - Refresh JWT token

    Args:
        params: {
            "refresh_token": str (optional, uses current session if not provided)
        }
    """
    if not is_supabase_configured():
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, "Supabase is not configured"
        )

    refresh_token = params.get("refresh_token")

    try:
        supabase = get_supabase_client()
        if not supabase:
            raise JSONRPCError(
                JSONRPCErrorCode.INTERNAL_ERROR, "Failed to initialize Supabase client"
            )

        if refresh_token:
            # Use refresh token to get new session via Supabase REST API
            # The Python client's refresh_session() uses current session, so we call API directly
            import httpx
            from app.config import settings

            anon_key = settings.supabase_anon_key
            if not anon_key:
                raise JSONRPCError(
                    JSONRPCErrorCode.INTERNAL_ERROR,
                    "Supabase anon key is not configured",
                )
            with httpx.Client() as client:
                resp = client.post(
                    f"{settings.supabase_url}/auth/v1/token?grant_type=refresh_token",
                    headers={
                        "apikey": anon_key,
                        "Content-Type": "application/json",
                    },
                    json={"refresh_token": refresh_token},
                )
                if resp.status_code != 200:
                    raise JSONRPCError(
                        JSONRPCErrorCode.AUTHENTICATION_ERROR,
                        f"Failed to refresh session: {resp.text}",
                    )

                data = resp.json()
                # Return session data in expected format
                return {
                    "success": True,
                    "session": {
                        "access_token": data.get("access_token"),
                        "refresh_token": data.get("refresh_token"),
                        "expires_in": data.get("expires_in", 3600),
                        "expires_at": data.get("expires_at"),
                        "token_type": data.get("token_type", "bearer"),
                    },
                }
        else:
            # Try to refresh current session
            response = supabase.auth.refresh_session()

            if not response or not response.session:
                raise JSONRPCError(
                    JSONRPCErrorCode.AUTHENTICATION_ERROR,
                    "Failed to refresh session - no active session or refresh token",
                )

        return {
            "success": True,
            "session": {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "expires_in": response.session.expires_in,
                "expires_at": response.session.expires_at,
                "token_type": response.session.token_type,
            },
        }

    except Exception as e:
        logger.error(f"Refresh error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.AUTHENTICATION_ERROR, f"Token refresh failed: {str(e)}"
        )


async def handle_auth_verify(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """
    Handle auth.verify - Verify JWT token validity

    Args:
        params: {
            "token": str (optional, uses current session if not provided)
        }
    """
    if not is_supabase_configured():
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, "Supabase is not configured"
        )

    token = params.get("token")

    try:
        # Use backend auth verification which handles both Supabase and legacy JWT
        from app.core.auth import verify_supabase_token

        if token:
            # Verify provided token
            user = verify_supabase_token(token)
            if user:
                return {"valid": True, "user": user}
            else:
                return {"valid": False, "error": "Invalid token"}
        else:
            # Verify current session - need Supabase client
            supabase = get_supabase_client()
            if not supabase:
                raise JSONRPCError(
                    JSONRPCErrorCode.INTERNAL_ERROR,
                    "Failed to initialize Supabase client",
                )

            response = supabase.auth.get_user()
            if response and response.user:
                return {
                    "valid": True,
                    "user": {
                        "id": response.user.id,
                        "email": response.user.email,
                        "user_metadata": response.user.user_metadata or {},
                        "app_metadata": response.user.app_metadata or {},
                    },
                }
            else:
                return {"valid": False, "error": "No active session"}

    except Exception as e:
        logger.error(f"Verify error: {e}")
        return {"valid": False, "error": str(e)}


async def handle_auth_reset_password_request(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """
    Handle auth.reset_password_request - Request password reset email

    Args:
        params: {
            "email": str
        }
    """
    if not is_supabase_configured():
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, "Supabase is not configured"
        )

    email = params.get("email")

    if not email:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Email is required")

    try:
        supabase = get_supabase_client()
        if not supabase:
            raise JSONRPCError(
                JSONRPCErrorCode.INTERNAL_ERROR, "Failed to initialize Supabase client"
            )

        # Request password reset
        reset_opts: Dict[str, str] = {}
        redirect_to = params.get("redirect_to")
        if isinstance(redirect_to, str) and redirect_to.strip():
            reset_opts["redirect_to"] = redirect_to
        supabase.auth.reset_password_for_email(
            email, cast(Options, reset_opts) if reset_opts else None
        )

        return {"success": True, "message": "Password reset email sent"}

    except Exception as e:
        logger.error(f"Reset password request error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Failed to send reset email: {str(e)}"
        )


async def handle_auth_reset_password(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """
    Handle auth.reset_password - Complete password reset with token

    Args:
        params: {
            "token": str (from email link),
            "new_password": str
        }
    """
    if not is_supabase_configured():
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, "Supabase is not configured"
        )

    token = params.get("token")
    new_password = params.get("new_password")

    if not token or not new_password:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Token and new_password are required"
        )

    try:
        supabase = get_supabase_client()
        if not supabase:
            raise JSONRPCError(
                JSONRPCErrorCode.INTERNAL_ERROR, "Failed to initialize Supabase client"
            )

        # Verify recovery token before updating password.
        verify_response = supabase.auth.verify_otp(
            cast(Any, {"type": "recovery", "token": token})
        )
        if not verify_response or not getattr(verify_response, "session", None):
            raise JSONRPCError(
                JSONRPCErrorCode.AUTHENTICATION_ERROR, "Invalid or expired reset token"
            )

        # Update password with verified recovery session
        response = supabase.auth.update_user(
            cast(UserAttributes, {"password": new_password})
        )

        return {
            "success": True,
            "message": "Password reset successfully",
            "user": (
                {"id": response.user.id, "email": response.user.email}
                if response.user
                else None
            ),
        }

    except Exception as e:
        logger.error(f"Reset password error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Password reset failed: {str(e)}"
        )


async def handle_auth_update_user(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """
    Handle auth.update_user - Update user metadata/profile

    Args:
        params: {
            "metadata": dict (user_metadata),
            "email": str (optional),
            "password": str (optional)
        }
    """
    user = await require_auth(user, "auth.update_user")

    if not is_supabase_configured():
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, "Supabase is not configured"
        )

    try:
        supabase = get_supabase_client()
        if not supabase:
            raise JSONRPCError(
                JSONRPCErrorCode.INTERNAL_ERROR, "Failed to initialize Supabase client"
            )

        update_data = {}

        if "metadata" in params:
            update_data["data"] = params["metadata"]

        if "email" in params:
            update_data["email"] = params["email"]

        if "password" in params:
            update_data["password"] = params["password"]

        if not update_data:
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_PARAMS, "No update data provided"
            )

        response = supabase.auth.update_user(cast(UserAttributes, update_data))

        if not response.user:
            raise JSONRPCError(JSONRPCErrorCode.INTERNAL_ERROR, "Failed to update user")

        return {
            "success": True,
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "user_metadata": response.user.user_metadata or {},
                "app_metadata": response.user.app_metadata or {},
            },
        }

    except Exception as e:
        logger.error(f"Update user error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"User update failed: {str(e)}"
        )


async def handle_auth_magic_link(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """
    Handle auth.magic_link - Send magic link email (passwordless)

    Args:
        params: {
            "email": str,
            "redirect_to": str (optional)
        }
    """
    if not is_supabase_configured():
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, "Supabase is not configured"
        )

    email = params.get("email")

    if not email:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Email is required")

    try:
        supabase = get_supabase_client()
        if not supabase:
            raise JSONRPCError(
                JSONRPCErrorCode.INTERNAL_ERROR, "Failed to initialize Supabase client"
            )

        # Send magic link
        magic_opts: Dict[str, str] = {}
        magic_redirect = params.get("redirect_to")
        if isinstance(magic_redirect, str) and magic_redirect.strip():
            magic_opts["email_redirect_to"] = magic_redirect
        otp_cred: SignInWithEmailAndPasswordlessCredentials = {"email": email}
        if magic_opts:
            otp_cred["options"] = cast(
                SignInWithEmailAndPasswordlessCredentialsOptions, magic_opts
            )
        supabase.auth.sign_in_with_otp(otp_cred)

        return {"success": True, "message": "Magic link email sent"}

    except Exception as e:
        logger.error(f"Magic link error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Failed to send magic link: {str(e)}"
        )


async def handle_auth_oauth_url(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """
    Handle auth.oauth_url - Get OAuth provider authorization URL

    Args:
        params: {
            "provider": str (e.g., "google", "github"),
            "redirect_to": str (optional)
        }
    """
    if not is_supabase_configured():
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, "Supabase is not configured"
        )

    provider = params.get("provider")

    if not provider:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Provider is required")

    try:
        supabase = get_supabase_client()
        if not supabase:
            raise JSONRPCError(
                JSONRPCErrorCode.INTERNAL_ERROR, "Failed to initialize Supabase client"
            )

        # Get OAuth URL
        oauth_opts: Dict[str, str] = {}
        oauth_redirect = params.get("redirect_to")
        if isinstance(oauth_redirect, str) and oauth_redirect.strip():
            oauth_opts["redirect_to"] = oauth_redirect
        oauth_cred: SignInWithOAuthCredentials = {
            "provider": cast(Provider, provider),
        }
        if oauth_opts:
            oauth_cred["options"] = cast(SignInWithOAuthCredentialsOptions, oauth_opts)
        response = supabase.auth.sign_in_with_oauth(oauth_cred)

        return {"success": True, "url": response.url, "provider": provider}

    except Exception as e:
        logger.error(f"OAuth URL error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Failed to get OAuth URL: {str(e)}"
        )


async def handle_auth_oauth_callback(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """
    Handle auth.oauth_callback - Handle OAuth callback and exchange code for session

    Args:
        params: {
            "code": str (from OAuth callback),
            "provider": str (optional, auto-detected)
        }
    """
    if not is_supabase_configured():
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, "Supabase is not configured"
        )

    code = params.get("code")

    if not code:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Code is required")

    try:
        supabase = get_supabase_client()
        if not supabase:
            raise JSONRPCError(
                JSONRPCErrorCode.INTERNAL_ERROR, "Failed to initialize Supabase client"
            )

        # Exchange OAuth code for session
        response = supabase.auth.exchange_code_for_session(code)
        session = getattr(response, "session", None)
        user_obj = getattr(response, "user", None)

        return {
            "success": True,
            "session": (
                {
                    "access_token": getattr(session, "access_token", None),
                    "refresh_token": getattr(session, "refresh_token", None),
                    "expires_at": getattr(session, "expires_at", None),
                    "expires_in": getattr(session, "expires_in", None),
                    "token_type": getattr(session, "token_type", None),
                }
                if session
                else None
            ),
            "user": (
                {
                    "id": getattr(user_obj, "id", None),
                    "email": getattr(user_obj, "email", None),
                }
                if user_obj
                else None
            ),
        }

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"OAuth callback failed: {str(e)}"
        )


def get_methods() -> Dict[str, Any]:
    """Return all auth methods from this module"""
    return {
        "auth.signup": handle_auth_signup,
        "auth.signin": handle_auth_signin,
        "auth.signout": handle_auth_signout,
        "auth.refresh": handle_auth_refresh,
        "auth.verify": handle_auth_verify,
        "auth.reset_password_request": handle_auth_reset_password_request,
        "auth.reset_password": handle_auth_reset_password,
        "auth.update_user": handle_auth_update_user,
        "auth.magic_link": handle_auth_magic_link,
        "auth.oauth_url": handle_auth_oauth_url,
        "auth.oauth_callback": handle_auth_oauth_callback,
    }
