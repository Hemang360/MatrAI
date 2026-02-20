"""
app/routers/vapi.py
--------------------
VAPI webhook handler for MatrAI inbound phone calls.

Event flow:
  1. Inbound call arrives → VAPI sends  `assistant-request`
     → We return a transient assistant whose firstMessage plays the
       consent prompt and exposes a `record_consent` tool for DTMF input.

  2. Caller presses 1 or 2 → VAPI triggers a `tool-calls` event
     with function name `record_consent` and parameter `digit`.
     → We write consent_given = True/False to Supabase and return
       an acknowledgement message that VAPI speaks aloud.

  3. All other events (status-update, end-of-call-report, etc.)
     → Acknowledged with HTTP 200, no action taken.

VAPI Payload Reference:
  https://docs.vapi.ai/server-url/events

Notes on DTMF:
  VAPI does NOT fire a raw DTMF event on its own. The standard pattern
  is to expose a `tool` (function) that the assistant's LLM calls when
  the user presses a key. We configure the assistant with a system
  prompt that maps "1" → accept and "2" → decline, and the LLM invokes
  `record_consent` with the detected digit.
"""

from __future__ import annotations

import logging
import secrets
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.prompts import INITIAL_SYSTEM_PROMPT
from app.routers.vapi_tool import COLLECT_SYMPTOMS_TOOL
from db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/vapi", tags=["VAPI"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# URL where the static consent audio is served.
# In production replace with your actual domain, e.g. "https://api.matrai.in"
_BASE_URL = "http://localhost:8000"
_CONSENT_AUDIO_URL = f"{_BASE_URL}/static/consent_hi.wav"


def _build_assistant(base_url: str = _BASE_URL) -> dict:
    """
    Build the transient VAPI assistant definition at call-time.

    Injecting base_url at runtime means we can point tool server URLs at
    the live ngrok tunnel (or production domain) without hardcoding.

    Args:
        base_url: Root URL of this FastAPI server (no trailing slash).
    """
    # Deep-copy the schema so we don't mutate the module-level constant
    import copy
    tool_def = copy.deepcopy(COLLECT_SYMPTOMS_TOOL)
    tool_def["server"]["url"] = f"{base_url}/vapi/tool"

    return {
        "firstMessage": (
            "Hum is call ko record karenge taaki doctor ise dekh sakein. "
            "Sehmati dene ke liye 1 dabayein, anyatha 2 dabayein."
        ),
        "voice": {
            "provider": "sarvam",
            "voiceId": "priya",
        },
        "model": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": INITIAL_SYSTEM_PROMPT,
                }
            ],
            "tools": [
                # Tool 1: Consent via DTMF keypress
                {
                    "type": "function",
                    "function": {
                        "name": "record_consent",
                        "description": (
                            "Records whether the caller consented to call recording. "
                            "Call this when the user presses 1 (consent) or 2 (decline)."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "digit": {
                                    "type": "string",
                                    "enum": ["1", "2"],
                                    "description": "DTMF digit: '1' = consent, '2' = decline.",
                                },
                                "phone_number": {
                                    "type": "string",
                                    "description": "Caller's phone number in E.164 format.",
                                },
                            },
                            "required": ["digit"],
                        },
                    },
                },
                # Tool 2: Symptom collection → triage (posts to /vapi/tool)
                tool_def,
            ],
        },
        "serverMessages": [
            "tool-calls",
            "status-update",
            "end-of-call-report",
        ],
    }


# ---------------------------------------------------------------------------
# Helper: update consent in Supabase
# ---------------------------------------------------------------------------

async def _update_consent(phone: str, consent: bool) -> None:
    """
    Upsert the user's consent_given flag in the `users` table.

    If no user row exists for this phone number yet, one is created
    (phone-first registration — common for IVR flows where the user
    hasn't gone through an app sign-up).

    Args:
        phone:   Caller's phone number (E.164 format, e.g. "+919876543210").
        consent: True if the caller pressed 1, False if they pressed 2.
    """
    supabase = get_supabase_client()

    result = (
        supabase
        .table("users")
        .upsert(
            {"phone": phone, "consent_given": consent},
            on_conflict="phone",        # update if phone already exists
        )
        .execute()
    )

    if not result.data:
        logger.warning("Supabase upsert returned no data for phone=%s", phone)
    else:
        logger.info(
            "Consent updated: phone=%s  consent_given=%s",
            phone, consent,
        )


# ---------------------------------------------------------------------------
# Webhook route
# ---------------------------------------------------------------------------

@router.post("/webhook", summary="VAPI server-side webhook")
async def vapi_webhook(
    request: Request,
    x_vapi_secret: str | None = Header(default=None, alias="x-vapi-secret"),
) -> JSONResponse:
    """
    Single entry-point for all VAPI server messages.

    VAPI sends a JSON body with a top-level `message` key containing
    a `type` discriminator field.  We dispatch on that type.

    Security:
        If VAPI_WEBHOOK_SECRET is set in .env, every incoming request
        is verified against the x-vapi-secret header using a
        constant-time comparison (secrets.compare_digest) to prevent
        timing attacks.  Requests with a missing or wrong secret are
        rejected with HTTP 401.

    Returns:
        JSONResponse — shape depends on the event type:
          - assistant-request  → { "assistant": { ... } }
          - tool-calls         → { "results": [ ... ] }
          - everything else    → {} (HTTP 200 acknowledgement)
    """
    # ------------------------------------------------------------------
    # Verify VAPI webhook secret (if configured)
    # ------------------------------------------------------------------
    _settings = get_settings()
    expected_secret: str | None = getattr(_settings, "vapi_webhook_secret", None)

    if expected_secret and not expected_secret.startswith("your_"):
        if not x_vapi_secret:
            logger.warning("Webhook request missing x-vapi-secret header — rejected")
            raise HTTPException(status_code=401, detail="Missing webhook secret")
        if not secrets.compare_digest(x_vapi_secret, expected_secret):
            logger.warning("Webhook request has invalid x-vapi-secret — rejected")
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

    try:
        body: dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    message: dict[str, Any] = body.get("message", {})
    event_type: str = message.get("type", "unknown")

    logger.info("VAPI webhook received: type=%s", event_type)

    # ------------------------------------------------------------------
    # 1. assistant-request — inbound call just connected
    # ------------------------------------------------------------------
    if event_type == "assistant-request":
        return await _handle_assistant_request(message)

    # ------------------------------------------------------------------
    # 2. tool-calls — LLM invoked our record_consent function
    # ------------------------------------------------------------------
    if event_type == "tool-calls":
        return await _handle_tool_calls(message)

    # ------------------------------------------------------------------
    # 3. status-update — log meaningful status transitions
    # ------------------------------------------------------------------
    if event_type == "status-update":
        status = message.get("status", "unknown")
        call_id = message.get("call", {}).get("id", "?")
        logger.info("Call %s status → %s", call_id, status)
        return JSONResponse({})

    # ------------------------------------------------------------------
    # 4. end-of-call-report — log summary, no action needed yet
    # ------------------------------------------------------------------
    if event_type == "end-of-call-report":
        call_id = message.get("call", {}).get("id", "?")
        ended_reason = message.get("endedReason", "unknown")
        logger.info("Call %s ended. Reason: %s", call_id, ended_reason)
        return JSONResponse({})

    # ------------------------------------------------------------------
    # 5. All other events — acknowledge silently
    # ------------------------------------------------------------------
    logger.debug("Unhandled VAPI event type: %s — acknowledged", event_type)
    return JSONResponse({})


# ---------------------------------------------------------------------------
# Sub-handlers
# ---------------------------------------------------------------------------

async def _handle_assistant_request(message: dict) -> JSONResponse:
    """
    Respond to an inbound call with a transient assistant.

    The assistant has two tools:
      1. record_consent  — consent via DTMF (posts to /vapi/webhook)
      2. collect_symptoms — triage engine (posts to /vapi/tool)

    VAPI requires a response within 7.5 seconds. We build the assistant
    definition synchronously — no DB calls in the hot path.
    """
    call = message.get("call", {})
    caller_phone = (
        call.get("customer", {}).get("number")
        or call.get("phoneNumber", {}).get("number")
        or "unknown"
    )
    call_id = call.get("id", "unknown")

    logger.info(
        "Inbound call: id=%s  caller=%s — returning MatrAI assistant",
        call_id, caller_phone,
    )

    # Resolve base_url from settings if configured, else fall back to default
    _settings = get_settings()
    base_url: str = getattr(_settings, "base_url", _BASE_URL) or _BASE_URL

    return JSONResponse({"assistant": _build_assistant(base_url)})


async def _handle_tool_calls(message: dict) -> JSONResponse:
    """
    Handle DTMF consent captured by the `record_consent` function tool.

    VAPI sends a list of tool invocations in `toolWithToolCallList`.
    We look for `record_consent`, read the `digit` parameter, and
    update Supabase accordingly.

    Response shape required by VAPI:
        { "results": [ { "toolCallId": "...", "result": "..." } ] }
    """
    call = message.get("call", {})
    caller_phone: str = (
        call.get("customer", {}).get("number")
        or call.get("phoneNumber", {}).get("number")
        or "unknown"
    )

    tool_list: list[dict] = message.get("toolWithToolCallList", [])
    results: list[dict] = []

    for tool in tool_list:
        function_name: str = tool.get("name", "")
        tool_call: dict = tool.get("toolCall", {})
        tool_call_id: str = tool_call.get("id", "unknown")
        parameters: dict = tool_call.get("parameters", {})

        if function_name != "record_consent":
            # Unknown function — return a neutral result so VAPI doesn't hang
            logger.warning("Unknown tool called: %s", function_name)
            results.append({
                "toolCallId": tool_call_id,
                "result": "Function not recognised.",
            })
            continue

        digit: str = str(parameters.get("digit", "")).strip()
        phone: str = parameters.get("phone_number") or caller_phone

        if digit == "1":
            consent = True
            spoken_result = (
                "Aapki sehmati darj kar li gayi hai. Dhanyavaad. "
                "Ab hum aapki madad ke liye taiyaar hain."
            )
        elif digit == "2":
            consent = False
            spoken_result = (
                "Aapne mana kar diya. Hum call record nahi karenge. "
                "Aap phir bhi sahayta le sakti hain."
            )
        else:
            logger.warning("record_consent called with unexpected digit=%r", digit)
            results.append({
                "toolCallId": tool_call_id,
                "result": "Maafi chahiye, mujhe samajh nahi aaya. Kripya 1 ya 2 dabayein.",
            })
            continue

        # Write to Supabase (non-blocking in the async context)
        try:
            await _update_consent(phone=phone, consent=consent)
        except Exception as exc:
            # DB failure must NOT drop the call — log and continue
            logger.error(
                "Failed to update consent for phone=%s: %s", phone, exc
            )
            spoken_result += " (Record nahi hua, kripya baad mein try karein.)"

        logger.info(
            "record_consent: phone=%s  digit=%s  consent=%s",
            phone, digit, consent,
        )

        results.append({
            "toolCallId": tool_call_id,
            "result": spoken_result,   # VAPI speaks this aloud to the caller
        })

    return JSONResponse({"results": results})
