#!/usr/bin/env python3
"""
scripts/create_vapi_assistant.py
---------------------------------
Creates a persistent VAPI assistant with Sarvam (Priya) voice
and stores the assistantId in .env as VAPI_ASSISTANT_ID.

Run ONCE. After that, make_call.py uses the stored ID.

Usage:
    cd MatrAI/backend
    venv/bin/python scripts/create_vapi_assistant.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Load .env first
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

from app.routers.vapi import _build_assistant  # noqa: E402
from app.config import get_settings  # noqa: E402

BASE_URL     = os.environ.get("BASE_URL", "http://localhost:8000")
VAPI_API_KEY = os.environ["VAPI_API_KEY"]

# Build the assistant definition (with sarvam voice intact)
assistant = _build_assistant(base_url=BASE_URL)
# Remove firstMessage for the persistent assistant
# (it's a greeting; kept as is for inbound, fine for outbound too)

print("Creating VAPI assistant with Sarvam / Priya voice...")
print(f"  BASE_URL: {BASE_URL}")
print(f"  Voice   : sarvam / priya")

try:
    resp = httpx.post(
        "https://api.vapi.ai/assistant",
        headers={
            "Authorization": f"Bearer {VAPI_API_KEY}",
            "Content-Type":  "application/json",
        },
        json=assistant,
        timeout=15.0,
    )
    resp.raise_for_status()
    data = resp.json()
    assistant_id: str = data["id"]
    print(f"\n✅  Assistant created!")
    print(f"    ID   : {assistant_id}")
    print(f"    Name : {data.get('name', '(unnamed)')}")

    # Write VAPI_ASSISTANT_ID to .env
    env_text  = env_path.read_text()
    if "VAPI_ASSISTANT_ID=" in env_text:
        # Update existing
        lines = []
        for line in env_text.splitlines():
            if line.startswith("VAPI_ASSISTANT_ID="):
                lines.append(f"VAPI_ASSISTANT_ID={assistant_id}")
            else:
                lines.append(line)
        env_path.write_text("\n".join(lines) + "\n")
    else:
        # Append
        env_path.write_text(env_text.rstrip() + f"\nVAPI_ASSISTANT_ID={assistant_id}\n")

    print(f"\n    Saved to .env → VAPI_ASSISTANT_ID={assistant_id}")
    print("\n    You can now run:  venv/bin/python scripts/make_call.py")

except httpx.HTTPStatusError as e:
    print(f"\n❌  VAPI API error: HTTP {e.response.status_code}")
    print(f"    {e.response.text}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌  Error: {e}")
    sys.exit(1)
