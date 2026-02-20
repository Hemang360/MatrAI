"""
app/routers/vapi_tool.py
-------------------------
Dedicated endpoint for the `collect_symptoms` VAPI tool call.

Why a separate router?
  VAPI supports per-tool `server.url` — meaning each tool can POST to
  its own endpoint rather than the main webhook. This keeps the symptom
  collection logic isolated, independently testable, and easy to extend.

Flow:
  LLM calls collect_symptoms(bleeding, headache, fetal_movement, ...)
      │
      ▼
  POST /vapi/tool
      │   Maps LLM params → evaluate_risk() input format
      │   Runs PMSMA triage engine
      │   Returns result as a VAPI tool result string
      ▼
  VAPI speaks the result to the caller (via the system prompt instructions)

Tool JSON schema (registered with the VAPI assistant in vapi.py):
  collect_symptoms({
      bleeding         : "none" | "light" | "heavy"
      headache         : boolean
      fetal_movement   : "normal" | "decreased" | "absent"
      weeks_pregnant   : integer (1–42)
      fever            : boolean (optional)
      swelling_feet    : boolean (optional)
      abdominal_pain   : "none" | "mild" | "severe" (optional)
      convulsions      : boolean (optional)
  })
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.prompts import build_system_prompt
from app.triage import evaluate_risk

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vapi", tags=["VAPI Tool"])


# ---------------------------------------------------------------------------
# Tool JSON Schema (exported so vapi.py can embed it in the assistant def)
# ---------------------------------------------------------------------------

COLLECT_SYMPTOMS_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "collect_symptoms",
        "description": (
            "Collect the pregnant caller's symptoms and run an obstetric risk "
            "assessment using PMSMA (Government of India) guidelines. "
            "Call this AFTER the caller has answered all symptom questions. "
            "Pass every symptom the user described, using defaults for anything "
            "not mentioned."
        ),
        "parameters": {
            "type": "object",
            "properties": {

                # === Core symptoms (always collected) ==========================

                "bleeding": {
                    "type": "string",
                    "enum": ["none", "light", "heavy"],
                    "description": (
                        "Vaginal bleeding status. 'heavy' = soaking a pad in under an hour "
                        "or blood clots; 'light' = spotting; 'none' = no bleeding."
                    ),
                },
                "headache": {
                    "type": "boolean",
                    "description": (
                        "True if the caller reports a severe, persistent headache "
                        "(sar mein bahut tej dard) especially with visual disturbances."
                    ),
                },
                "fetal_movement": {
                    "type": "string",
                    "enum": ["normal", "decreased", "absent"],
                    "description": (
                        "Baby's movement in the last 12 hours. "
                        "'decreased' = noticeably less than usual; "
                        "'absent' = no movement felt at all."
                    ),
                },
                "weeks_pregnant": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 45,
                    "description": (
                        "Gestational age in weeks. Convert from months if needed: "
                        "1 month ≈ 4 weeks. If unknown, use 0."
                    ),
                },

                # === Extended symptoms (collect if mentioned) ==================

                "fever": {
                    "type": "boolean",
                    "description": "True if the caller has bukhar (fever / body feels hot).",
                },
                "swelling_feet": {
                    "type": "boolean",
                    "description": (
                        "True if the caller has sudden or severe swelling of the feet "
                        "or face (pair ya chehra phool gaya)."
                    ),
                },
                "abdominal_pain": {
                    "type": "string",
                    "enum": ["none", "mild", "severe"],
                    "description": (
                        "Abdominal/pelvic pain level. "
                        "'mild' = tolerable discomfort; 'severe' = intense, possibly rhythmic."
                    ),
                },
                "convulsions": {
                    "type": "boolean",
                    "description": (
                        "True if the caller had or is currently having fits / "
                        "dore (haath-pair kaanpna, ankhen palat jaana)."
                    ),
                },
            },

            # Only the 4 specified in the chunk are required.
            # All others default gracefully to "none" / False / "normal".
            "required": ["bleeding", "headache", "fetal_movement", "weeks_pregnant"],
        },
    },
    # Tell VAPI to POST this tool call to our dedicated endpoint
    "server": {
        "url": "PLACEHOLDER_REPLACED_AT_RUNTIME",   # replaced in vapi.py build fn
    },
}


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/tool", summary="VAPI tool endpoint — collect_symptoms")
async def vapi_tool(request: Request) -> JSONResponse:
    """
    Receives a VAPI `tool-calls` event for the `collect_symptoms` function,
    maps the LLM parameters to evaluate_risk() input format, runs the triage
    engine, and returns a structured result string that VAPI feeds back to
    the LLM to speak aloud.

    Emergency transfer (RED):
        If triage returns RED, we ALSO fire a background VAPI Control API
        call to transfer the call to DOCTOR_PHONE_NUMBER. This happens
        concurrently with returning the tool result so there's no delay.
        The tool result instructs the LLM to speak the bridge message;
        the control API then physically transfers the call.

    Expected VAPI payload:
        {
          "message": {
            "type": "tool-calls",
            "call": { "id": "...", "customer": { "number": "+91..." } },
            "toolWithToolCallList": [{
              "name": "collect_symptoms",
              "toolCall": {
                "id": "tc_xxx",
                "parameters": {
                  "bleeding": "heavy",
                  "headache": true,
                  "fetal_movement": "decreased",
                  "weeks_pregnant": 28,
                  ...
                }
              }
            }]
          }
        }
    """
    try:
        body: dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    message: dict = body.get("message", {})
    event_type: str = message.get("type", "unknown")

    if event_type != "tool-calls":
        logger.warning("Unexpected event type at /vapi/tool: %s", event_type)
        return JSONResponse({})

    call: dict        = message.get("call", {})
    call_id: str      = call.get("id", "unknown")
    control_url: str  = call.get("controlUrl", "")

    tool_list: list[dict] = message.get("toolWithToolCallList", [])
    results: list[dict]   = []

    for tool in tool_list:
        function_name: str = tool.get("name", "")
        tool_call: dict    = tool.get("toolCall", {})
        tool_call_id: str  = tool_call.get("id", "unknown")
        params: dict       = tool_call.get("parameters", {})

        if function_name != "collect_symptoms":
            logger.warning("Unknown tool at /vapi/tool: %s", function_name)
            results.append({
                "toolCallId": tool_call_id,
                "result": json.dumps({"error": f"Unknown function: {function_name}"}),
            })
            continue

        result_str, risk_level = _run_triage(params, tool_call_id)
        results.append({
            "toolCallId": tool_call_id,
            "result": result_str,
        })

        # Fire transfer in background so we don't delay the tool response
        if risk_level == "RED" and control_url:
            asyncio.create_task(
                _transfer_to_doctor(control_url=control_url, call_id=call_id)
            )
        elif risk_level == "RED" and not control_url:
            logger.warning(
                "RED alert on call %s but no controlUrl — transfer skipped. "
                "Ensure serverMessages includes 'tool-calls' with call object.",
                call_id,
            )

    return JSONResponse({"results": results})


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

_BRIDGE_MESSAGE = (
    "Behen, aapki sthiti gambhir lag rahi hai. "
    "Main aapko doctor se connect kar rahi hoon."
)


async def _transfer_to_doctor(control_url: str, call_id: str) -> None:
    """
    Call the VAPI Live Call Control API to transfer the call to the doctor.

    This runs as a background asyncio task so the tool result is returned
    to VAPI immediately (LLM starts speaking the bridge message) while the
    transfer request is in-flight.

    VAPI Control API shape:
        POST {controlUrl}
        { "type": "transfer",
          "destination": { "type": "number", "number": "+91..." },
          "content": "<spoken before transfer>" }

    Ref: https://docs.vapi.ai/calls/call-features (Transfer Call section)
    """
    settings = get_settings()
    doctor_number: str = getattr(settings, "doctor_phone_number", "").strip()

    if not doctor_number or doctor_number.startswith("your_"):
        logger.error(
            "RED alert on call %s but DOCTOR_PHONE_NUMBER not set in .env — "
            "transfer aborted.",
            call_id,
        )
        return

    payload = {
        "type": "transfer",
        "destination": {
            "type": "number",
            "number": doctor_number,
        },
        "content": _BRIDGE_MESSAGE,
    }

    logger.info(
        "RED emergency: transferring call %s to doctor %s",
        call_id, doctor_number,
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(control_url, json=payload)
            resp.raise_for_status()
            logger.info(
                "Transfer request accepted for call %s: HTTP %s",
                call_id, resp.status_code,
            )
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Transfer failed for call %s: HTTP %s — %s",
            call_id, exc.response.status_code, exc.response.text,
        )
    except Exception as exc:
        logger.error("Transfer error for call %s: %s", call_id, exc)


def _run_triage(params: dict, tool_call_id: str) -> tuple[str, str]:
    """
    Map LLM tool parameters → evaluate_risk() input, run triage.

    Returns:
        tuple of (result_json_string, risk_level)
        risk_level is returned separately so the caller can branch on RED.
    """
    weeks: int = int(params.get("weeks_pregnant", 0))

    symptoms: dict = {
        "bleeding":        params.get("bleeding", "none"),
        "severe_headache": bool(params.get("headache", False)),
        "fetal_movement":  params.get("fetal_movement", "normal"),
        "fever":           bool(params.get("fever", False)),
        "swelling_feet":   bool(params.get("swelling_feet", False)),
        "abdominal_pain":  params.get("abdominal_pain", "none"),
        "convulsions":     bool(params.get("convulsions", False)),
    }

    logger.info(
        "collect_symptoms called: weeks=%d  symptoms=%s  tool_call_id=%s",
        weeks, symptoms, tool_call_id,
    )

    try:
        triage: dict = evaluate_risk(symptoms)
    except Exception as exc:
        logger.error("evaluate_risk raised an exception: %s", exc)
        return json.dumps({
            "error": "Triage engine error. Please advise caller to visit nearest PHC.",
            "risk_level": "YELLOW",
        }), "YELLOW"

    risk_level: str       = triage["risk_level"]
    mandatory_action: str  = triage["mandatory_action"]
    clinical_reason: str   = triage["clinical_reason"]

    logger.info(
        "Triage result: risk=%s  weeks=%d  action=%r",
        risk_level, weeks, mandatory_action[:60],
    )

    # For RED, prepend the bridge message so the LLM speaks it FIRST,
    # then the mandatory_action. The actual call transfer is triggered
    # as a separate background task in vapi_tool() above.
    if risk_level == "RED":
        spoken_instructions = (
            f"{_BRIDGE_MESSAGE} "
            f"TRIAGE COMPLETE. Risk level is RED. "
            f'You MUST say EXACTLY: "{mandatory_action}" '
            f"Then say: 'Behen, ABHI 108 par call karein. Yeh bahut zaroori hai.'"
        )
    else:
        spoken_instructions = (
            f"TRIAGE COMPLETE. Risk level is {risk_level}. "
            f"You MUST now say the following EXACTLY word-for-word: "
            f'"{mandatory_action}"'
        )

    result_payload = {
        "risk_level":       risk_level,
        "mandatory_action": mandatory_action,
        "clinical_reason":  clinical_reason,
        "weeks_pregnant":   weeks,
        "instructions":     spoken_instructions,
    }

    return json.dumps(result_payload, ensure_ascii=False), risk_level
