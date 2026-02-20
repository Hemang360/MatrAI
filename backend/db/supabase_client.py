"""
db/supabase_client.py
---------------------
Initializes and exposes a singleton Supabase client, plus higher-level
persistence helpers used across the app.

Public API:
    get_supabase_client()   → cached Client singleton
    get_or_create_user()    → upsert user by phone, return user_id (UUID)
    save_call_summary()     → insert completed call record into `calls` table
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from supabase import Client, create_client

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache()
def get_supabase_client() -> Client:
    """
    Return a cached Supabase client instance.

    The client is created once and reused for the lifetime of the process.
    Credentials are pulled from the app settings (loaded from .env).

    Returns:
        supabase.Client: An authenticated Supabase client.

    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_KEY are not set.
    """
    settings = get_settings()

    if not settings.supabase_url or not settings.supabase_key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_KEY must be set in your .env file."
        )

    client: Client = create_client(settings.supabase_url, settings.supabase_key)
    return client


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------

def get_or_create_user(phone: str) -> str | None:
    """
    Upsert a user row by phone number and return their UUID.

    If the user already exists (from a previous call or consent event),
    their existing row is returned unchanged. If they're new, a row is
    created with consent_given=False (they must still consent on a call).

    Args:
        phone: E.164 phone number, e.g. "+919876543210"

    Returns:
        str | None: user UUID string, or None if the upsert fails.
    """
    if not phone or phone == "unknown":
        return None

    supabase = get_supabase_client()
    try:
        result = (
            supabase
            .table("users")
            .upsert(
                {"phone": phone, "consent_given": False},
                on_conflict="phone",
                # ignoreDuplicates keeps existing row intact (consent stays True
                # if they already gave it — we don't downgrade it here)
            )
            .execute()
        )
        rows = result.data or []
        if not rows:
            # Row already existed and ignoreDuplicates suppressed output — fetch it
            fetch = (
                supabase
                .table("users")
                .select("id")
                .eq("phone", phone)
                .single()
                .execute()
            )
            return fetch.data.get("id") if fetch.data else None

        return rows[0].get("id")
    except Exception as exc:
        logger.error("get_or_create_user failed for phone=%s: %s", phone, exc)
        return None


# ---------------------------------------------------------------------------
# Call persistence
# ---------------------------------------------------------------------------

def save_call_summary(
    *,
    phone: str,
    vapi_call_id: str,
    transcript: str,
    risk_level: str | None,
    symptoms_json: dict | None,
    ai_advice: str,
) -> str | None:
    """
    Persist a completed call record to the `calls` table.

    This is called from the `end-of-call-report` webhook handler after VAPI
    sends the final transcript and summary. It:
      1. Resolves (or creates) the user row from their phone number.
      2. Inserts a new row in `calls` with transcript, triage result, and advice.
      3. If risk_level == "RED", also writes to `emergency_logs` for auditing.

    All DB errors are caught and logged — they must never propagate back
    to VAPI (which expects a clean HTTP 200 within seconds).

    Args:
        phone:         Caller's E.164 phone number.
        vapi_call_id:  The call ID from VAPI (stored as a note, not a FK).
        transcript:    Full call transcript text.
        risk_level:    "RED" | "YELLOW" | "GREEN" | None (if triage wasn't run).
        symptoms_json: Dict of collected symptoms (from collect_symptoms tool).
        ai_advice:     The mandatory_action text spoken by the AI.

    Returns:
        str | None: UUID of the new calls row, or None if insert failed.
    """
    supabase = get_supabase_client()

    # Step 1: Resolve user_id
    user_id = get_or_create_user(phone)
    if not user_id:
        logger.error(
            "save_call_summary: cannot resolve user_id for phone=%s  "
            "call_id=%s — skipping save.",
            phone, vapi_call_id,
        )
        return None

    # Step 2: Insert into calls
    call_row: dict[str, Any] = {
        "user_id":      user_id,
        "transcript":   transcript,
        "ai_advice":    ai_advice,
        "symptoms_json": symptoms_json or {},
    }
    # Only set risk_level if it's a valid enum value (schema: RED | YELLOW | GREEN)
    if risk_level in ("RED", "YELLOW", "GREEN"):
        call_row["risk_level"] = risk_level

    try:
        result = supabase.table("calls").insert(call_row).execute()
        rows = result.data or []
        if not rows:
            logger.error(
                "calls insert returned no data for user=%s  call=%s",
                user_id, vapi_call_id,
            )
            return None

        call_db_id: str = rows[0]["id"]
        logger.info(
            "Call saved: calls.id=%s  user=%s  risk=%s  vapi_call_id=%s",
            call_db_id, user_id, risk_level, vapi_call_id,
        )

        # Step 3: Write emergency_log for RED calls
        if risk_level == "RED":
            _log_emergency(supabase, call_id=call_db_id, user_id=user_id)

        return call_db_id

    except Exception as exc:
        logger.error(
            "save_call_summary DB error for user=%s  call=%s: %s",
            user_id, vapi_call_id, exc,
        )
        return None


def _log_emergency(supabase: Client, call_id: str, user_id: str) -> None:
    """
    Insert a row in emergency_logs for RED-level calls.
    notified_asha defaults to False — a future ASHA notification feature
    can update this to True once the alert is sent.
    """
    try:
        supabase.table("emergency_logs").insert({
            "call_id":       call_id,
            "user_id":       user_id,
            "notified_asha": False,
        }).execute()
        logger.info("Emergency log created for call=%s  user=%s", call_id, user_id)
    except Exception as exc:
        logger.error(
            "Failed to write emergency_log for call=%s: %s", call_id, exc
        )
