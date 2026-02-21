#!/usr/bin/env python3
"""
scripts/make_call.py
--------------------
Trigger a VAPI outbound call to the patient/demo number.

Flow:
  1. Run this script
  2. +919256881229 rings (the patient's phone / demo phone)
  3. Caller hears the Hindi MatrAI agent (Sarvam Priya voice)
  4. Agent collects symptoms via collect_symptoms tool
  5. If RED → call is transferred to DOCTOR_PHONE_NUMBER

First-time setup:
    venv/bin/python scripts/create_vapi_assistant.py   # creates assistant with Sarvam voice

Then every call:
    venv/bin/python scripts/make_call.py
    venv/bin/python scripts/make_call.py --to +91XXXXXXXXXX
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Load .env
# ---------------------------------------------------------------------------
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        v = v.split("#")[0].strip()
        os.environ.setdefault(k.strip(), v)

import httpx  # noqa: E402
sys.path.insert(0, str(Path(__file__).parent.parent))

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
VAPI_API_KEY    = os.environ["VAPI_API_KEY"]
# Prefer Twilio number (supports international calls); fall back to free VAPI number
PHONE_NUMBER_ID = (
    os.environ.get("VAPI_PHONE_NUMBER_ID", "").strip()
    or "77788218-75bf-4b7d-9783-3ba14ba298a2"   # free VAPI US number (fallback)
)
BASE_URL        = os.environ.get("BASE_URL", "http://localhost:8000")
ASSISTANT_ID    = os.environ.get("VAPI_ASSISTANT_ID", "").strip()
TOOL_ID         = os.environ.get("VAPI_TOOL_ID", "").strip()
DEFAULT_PATIENT = "+919256881229"

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Trigger MatrAI outbound call via VAPI")
parser.add_argument(
    "--to", default=DEFAULT_PATIENT,
    help=f"Phone number to call in E.164 format (default: {DEFAULT_PATIENT})"
)
args = parser.parse_args()
patient_number: str = args.to

# ---------------------------------------------------------------------------
# Build payload — prefer assistantId (Sarvam voice) over inline assistant
# ---------------------------------------------------------------------------
if ASSISTANT_ID:
    # Use the pre-created assistant with Sarvam voice.
    # Route via SIP URI (avoids "free numbers can't call international" limit)
    use_sip = bool(os.environ.get("VAPI_SIP_URI", "").strip())
    sip_uri  = os.environ.get("VAPI_SIP_URI", "").strip()

    if use_sip and sip_uri:
        payload = {
            "phoneNumberId": PHONE_NUMBER_ID,   # caller ID shown to the recipient
            "customer": {"number": patient_number},
            "assistantId": ASSISTANT_ID,
        }
        print(f"📞  Using persistent assistant (Sarvam / Priya voice)")
        print(f"    Assistant ID    : {ASSISTANT_ID}")
    else:
        payload = {
            "phoneNumberId": PHONE_NUMBER_ID,
            "customer": {"number": patient_number},
            "assistantId": ASSISTANT_ID,
        }
        print(f"📞  Using persistent assistant (Sarvam / Priya voice)")
        print(f"    Assistant ID    : {ASSISTANT_ID}")
else:
    # Fallback: inline assistant (openai voice — sarvam not accepted inline)
    print("⚠️   VAPI_ASSISTANT_ID not set. Falling back to openai/shimmer voice.")
    print("    Run: venv/bin/python scripts/create_vapi_assistant.py  to enable Sarvam.")
    from app.routers.vapi import _build_assistant  # noqa: E402
    assistant = _build_assistant(base_url=BASE_URL)
    assistant["voice"] = {"provider": "openai", "voiceId": "shimmer"}
    payload = {
        "phoneNumberId": PHONE_NUMBER_ID,
        "customer": {"number": patient_number},
        "assistant": assistant,
    }

# ---------------------------------------------------------------------------
# Make the call
# ---------------------------------------------------------------------------
print(f"\n📞  Calling {patient_number} via VAPI...")
print(f"    Phone Number ID : {PHONE_NUMBER_ID}")
print(f"    BASE_URL        : {BASE_URL}")

try:
    resp = httpx.post(
        "https://api.vapi.ai/call/phone",
        headers={
            "Authorization": f"Bearer {VAPI_API_KEY}",
            "Content-Type":  "application/json",
        },
        json=payload,
        timeout=15.0,
    )
    resp.raise_for_status()
    data = resp.json()
    print(f"\n✅  Call initiated!")
    print(f"    Call ID  : {data.get('id', '?')}")
    print(f"    Status   : {data.get('status', '?')}")
    print(f"\n    {patient_number} is now ringing... 📱")

except httpx.HTTPStatusError as e:
    print(f"\n❌  VAPI API error: HTTP {e.response.status_code}")
    print(f"    {e.response.text}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌  Error: {e}")
    sys.exit(1)
