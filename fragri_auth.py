"""Supabase authentication helpers for FR DataSync / Fragri.

This module is called by the Streamlit server. Do not expose the Supabase secret
key to the browser or commit Streamlit secrets to GitHub.
"""
from __future__ import annotations

from typing import Any
from datetime import datetime, timezone
from html import escape

import streamlit as st
from supabase import Client, create_client


APP_URL = "https://fragri.streamlit.app"


def _secret_value(section: str, key: str) -> str:
    try:
        value = st.secrets[section][key]
    except Exception as exc:
        raise RuntimeError(
            f"Missing Streamlit Secret [{section}] {key}. "
            "Check your app's Settings > Secrets."
        ) from exc
    value = str(value).strip()
    if not value:
        raise RuntimeError(
            f"Streamlit Secret [{section}] {key} is empty."
        )
    return value


@st.cache_resource
def _make_admin_client() -> Client:
    """Privileged client used only by trusted server-side database operations."""
    url = _secret_value("fragri_database", "url")
    secret_key = _secret_value("fragri_database", "secret_key")
    return create_client(url, secret_key)


def _get_auth_client() -> Client:
    """Keep one auth client in this Streamlit browser session for OAuth PKCE."""
    if "fragri_supabase_auth_client" not in st.session_state:
        try:
            auth_secrets = st.secrets["connections"]["supabase"]
            url = str(auth_secrets["url"]).strip()
            publishable_key = str(auth_secrets["key"]).strip()
        except Exception as exc:
            raise RuntimeError(
                "Missing [connections.supabase] url/key in Streamlit Secrets."
            ) from exc
        if not url or not publishable_key:
            raise RuntimeError(
                "The Supabase URL and publishable key must not be empty."
            )
        st.session_state["fragri_supabase_auth_client"] = create_client(
            url, publishable_key
        )
    return st.session_state["fragri_supabase_auth_client"]


def _session_user(client: Client) -> Any | None:
    try:
        session = client.auth.get_session()
        return getattr(session, "user", None) if session else None
    except Exception:
        return None


def _write_profile_and_login_event(user: Any) -> None:
    """Upsert the authenticated user's profile and record one login per session."""
    user_id = getattr(user, "id", None)
    if not user_id:
        return

    already_synced = st.session_state.get("fragri_profile_synced_user")
    if already_synced == user_id:
        return

    metadata = getattr(user, "user_metadata", None) or {}
    email = getattr(user, "email", None)
    full_name = (
        metadata.get("full_name")
        or metadata.get("name")
        or metadata.get("display_name")
        or (email.split("@")[0] if email else "Fragri user")
    )
    avatar_url = metadata.get("avatar_url") or metadata.get("picture")

    try:
        admin = _make_admin_client()
        admin.table("user_profiles").upsert(
            {
                "user_id": user_id,
                "email": email,
                "full_name": full_name,
                "avatar_url": avatar_url,
                "last_login_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="user_id",
        ).execute()
        admin.table("activity_logs").insert(
            {
                "user_id": user_id,
                "action": "login",
                "tool_name": "Fragri",
                "status": "success",
                "details": {"provider": metadata.get("provider", "email_or_oauth")},
            }
        ).execute()
        st.session_state["fragri_profile_synced_user"] = user_id
    except Exception as exc:
        # Authentication should not silently fail because profile logging failed.
        # Keep details out of the UI; the error may contain database information.
        st.warning(
            "You are signed in, but Fragri could not save your profile/activity "
            "record. Check the Supabase tables and Streamlit Secrets."
        )
        st.session_state["fragri_profile_error"] = type(exc).__name__


def log_activity(
    action: str,
    tool_name: str = "FR DataSync Merger",
    status: str = "success",
    details: dict | None = None,
) -> None:
    """Record metadata-only activity for the currently authenticated user."""
    client = _get_auth_client()
    user = _session_user(client)
    user_id = getattr(user, "id", None) if user else None
    if not user_id:
        return

    safe_status = status if status in {"success", "failure", "info"} else "info"
    # Do not pass filenames, spreadsheet rows, Aadhaar/mobile numbers, or file contents.
    try:
        _make_admin_client().table("activity_logs").insert(
            {
                "user_id": user_id,
                "action": action[:100],
                "tool_name": tool_name[:100],
                "status": safe_status,
                "details": details or {},
            }
        ).execute()
    except Exception:
        # Logging should not interrupt file processing or report download.
        pass


def require_login() -> dict:
    """Render login/register UI; return a minimal authenticated user profile."""
    st.session_state.setdefault("fragri_auth_mode", "Log in")

    try:
        client = _get_auth_client()
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()

    # Supabase redirects back to the app with ?code=... for the PKCE exchange.
    code = st.query_params.get("code")
    if code:
        try:
            client.auth.exchange_code_for_session(code)
            st.query_params.clear()
            st.rerun()
        except Exception:
            st.query_params.clear()
            st.error(
                "Google sign-in could not be completed. Please try again. "
                "If the problem continues, check Supabase URL Configuration "
                "and the Google OAuth callback URL."
            )

    oauth_error = st.query_params.get("error_description") or st.query_params.get("error")
    if oauth_error:
        st.query_params.clear()
        st.error("Google sign-in was cancelled or could not be completed. Please try again.")

    user = _session_user(client)
    if user:
        _write_profile_and_login_event(user)
        email = getattr(user, "email", None) or "Signed-in user"
        with st.sidebar:
            st.caption(f"Signed in as {email}")
            if st.button("Log out", use_container_width=True, key="fragri_logout"):
                try:
                    client.auth.sign_out()
                finally:
                    for key in (
                        "fragri_profile_synced_user",
                        "fragri_profile_error",
                        "fragri_process_logged_fingerprint",
                    ):
                        st.session_state.pop(key, None)
                    st.rerun()
        return {
            "id": getattr(user, "id", None),
            "email": getattr(user, "email", None),
            "user_metadata": getattr(user, "user_metadata", None) or {},
        }

    st.markdown(
        """
        <div style="text-align:center;padding:1rem 0 .5rem">
          <h1 style="color:#1b5e20;margin-bottom:.2rem">Welcome to Fragri</h1>
          <p style="color:#47734b">Sign in to access FR DataSync tools.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    mode = st.radio(
        "Choose an option",
        ["Log in", "Create account"],
        horizontal=True,
        key="fragri_auth_mode",
    )

    if mode == "Create account":
        with st.form("fragri_signup_form", clear_on_submit=False):
            full_name = st.text_input("Full name", max_chars=120)
            email = st.text_input("Email address").strip()
            password = st.text_input("Password (at least 8 characters)", type="password")
            confirm = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button(
                "Create account", use_container_width=True
            )

        if submitted:
            if not full_name.strip():
                st.error("Enter your full name.")
            elif not email or "@" not in email:
                st.error("Enter a valid email address.")
            elif len(password) < 8:
                st.error("Use a password with at least 8 characters.")
            elif password != confirm:
                st.error("The passwords do not match.")
            else:
                try:
                    response = client.auth.sign_up(
                        {
                            "email": email,
                            "password": password,
                            "options": {"data": {"full_name": full_name.strip()}},
                        }
                    )
                    if getattr(response, "session", None):
                        st.success("Account created. You are now signed in.")
                        st.rerun()
                    else:
                        st.success(
                            "Account created. Check your email for the confirmation "
                            "link, then return here and log in."
                        )
                except Exception:
                    st.error(
                        "Registration failed. The email may already be registered, "
                        "or Supabase email confirmation may need configuration."
                    )

    else:
        with st.form("fragri_login_form", clear_on_submit=False):
            email = st.text_input("Email address").strip()
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Enter your email address and password.")
            else:
                try:
                    client.auth.sign_in_with_password(
                        {"email": email, "password": password}
                    )
                    st.rerun()
                except Exception:
                    st.error(
                        "Login failed. Check your email and password, and confirm "
                        "your email address if confirmation is enabled."
                    )

    st.divider()
    st.markdown("#### Or")
    if st.button("Continue with Google", use_container_width=True, key="fragri_google_login"):
        try:
            response = client.auth.sign_in_with_oauth(
                {
                    "provider": "google",
                    "options": {"redirect_to": APP_URL},
                }
            )
            oauth_url = getattr(response, "url", None)
            if not oauth_url:
                data = getattr(response, "data", None)
                oauth_url = getattr(data, "url", None) if data else None
            if not oauth_url:
                st.error("Supabase did not return a Google sign-in URL.")
            else:
                # Same-tab navigation is important for the PKCE verifier/session.
                safe_oauth_url = escape(oauth_url, quote=True)
                st.markdown(
                    f'<a href="{safe_oauth_url}" target="_self" '
                    'style="display:inline-block;padding:0.7rem 1rem;'
                    'background:#2e7d32;color:white;border-radius:10px;'
                    'text-decoration:none;font-weight:700">'
                    'Continue to Google</a>',
                    unsafe_allow_html=True,
                )
                st.info("Select **Continue to Google** to finish signing in.")
        except Exception:
            st.error(
                "Could not start Google sign-in. Check that Google is enabled in "
                "Supabase and the callback/redirect URLs match."
            )

    st.caption("By continuing, you agree to use Fragri responsibly and not upload data you are not authorised to process.")
    st.stop()
