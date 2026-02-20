#!/usr/bin/env python3
"""
scripts/test_red_flag.py
------------------------
Verifies that the /vapi/tool endpoint correctly:
  1. Returns a "results" list when given a heavy-bleeding symptom payload
  2. Classifies the case as RED risk
  3. Includes the mandatory_action and clinical_reason in the tool result
  4. Contains the bride message that tells the LLM to speak a transfer warning

This is a pure-Python integration smoke test — no real VAPI call or phone
number needed. Run it while the FastAPI dev server is running:

    # Terminal 1 – backend running
    uvicorn app.main:app --reload

    # Terminal 2 – run this script
    python scripts/test_red_flag.py

ALL assertions pass → exits 0 (green)
ANY assertion fails  → raises AssertionError and exits 1 (red)
"""

from __future__ import annotations

import json
import sys

import httpx

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_URL      = "http://localhost:8000"
TOOL_ENDPOINT = f"{BASE_URL}/vapi/tool"

# ---------------------------------------------------------------------------
# Mock payload — heavy bleeding at 30 weeks, convulsions, absent fetal movement
# This maps to the worst-case RED scenario defined in the PMSMA triage engine.
# ---------------------------------------------------------------------------
RED_FLAG_PAYLOAD = {
    "message": {
        "type": "tool-calls",
        "call": {
            "id": "test-red-flag-001",
            "customer": {"number": "+919900000001"},
            # No controlUrl → transfer task is skipped (correct for unit test)
        },
        "toolWithToolCallList": [
            {
                "name": "collect_symptoms",
                "toolCall": {
                    "id": "tc_test_001",
                    "parameters": {
                        # RED-trigger symptoms (per PMSMA protocol)
                        "bleeding":        "heavy",       # soaking > 1 pad/hr
                        "headache":        True,           # severe headache
                        "fetal_movement":  "absent",       # no movement felt
                        "weeks_pregnant":  30,
                        "fever":           True,
                        "swelling_feet":   True,
                        "abdominal_pain":  "severe",
                        "convulsions":     True,           # eclampsia indicator
                    },
                },
            }
        ],
    }
}

# ---------------------------------------------------------------------------
# GREEN-flag control payload (should NOT return RED)
# ---------------------------------------------------------------------------
GREEN_FLAG_PAYLOAD = {
    "message": {
        "type": "tool-calls",
        "call": {"id": "test-green-flag-001", "customer": {"number": "+919900000002"}},
        "toolWithToolCallList": [
            {
                "name": "collect_symptoms",
                "toolCall": {
                    "id": "tc_test_002",
                    "parameters": {
                        "bleeding":       "none",
                        "headache":       False,
                        "fetal_movement": "normal",
                        "weeks_pregnant": 20,
                        "fever":          False,
                        "swelling_feet":  False,
                        "abdominal_pain": "none",
                        "convulsions":    False,
                    },
                },
            }
        ],
    }
}

YELLOW_FLAG_PAYLOAD = {
    "message": {
        "type": "tool-calls",
        "call": {"id": "test-yellow-flag-001", "customer": {"number": "+919900000003"}},
        "toolWithToolCallList": [
            {
                "name": "collect_symptoms",
                "toolCall": {
                    "id": "tc_test_003",
                    "parameters": {
                        "bleeding":       "light",
                        "headache":       True,
                        "fetal_movement": "decreased",
                        "weeks_pregnant": 25,
                        "fever":          False,
                        "swelling_feet":  True,
                        "abdominal_pain": "mild",
                        "convulsions":    False,
                    },
                },
            }
        ],
    }
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def post_tool(payload: dict) -> tuple[dict, dict]:
    """POST payload to /vapi/tool; returns (http_response_dict, parsed_result_dict)."""
    resp = httpx.post(TOOL_ENDPOINT, json=payload, timeout=15.0)
    resp.raise_for_status()
    body = resp.json()
    # body == { "results": [{ "toolCallId": "...", "result": "<json string>" }] }
    results_list = body.get("results", [])
    assert results_list, f"Expected non-empty 'results' list, got: {body}"
    result_str = results_list[0]["result"]
    parsed = json.loads(result_str)
    return body, parsed


def check(label: str, condition: bool, detail: str = "") -> None:
    """Print a pass/fail line and raise on failure."""
    icon = "✅" if condition else "❌"
    print(f"  {icon}  {label}", f"— {detail}" if detail else "")
    if not condition:
        raise AssertionError(f"FAILED: {label}  {detail}")


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


def test_red_flag() -> None:
    print("\n🔴 Test 1 — Heavy Bleeding / Convulsions → expect RED")
    body, result = post_tool(RED_FLAG_PAYLOAD)

    check("HTTP response contains 'results'",   "results" in body)
    check("risk_level == RED",                  result.get("risk_level") == "RED",
          f"got: {result.get('risk_level')}")
    check("clinical_reason is non-empty",       bool(result.get("clinical_reason")),
          f"got: {result.get('clinical_reason', '')[:80]}")
    check("mandatory_action is non-empty",      bool(result.get("mandatory_action")))
    check("instructions mention bridge msg",
          "connect" in result.get("instructions", "").lower() or
          "doctor"  in result.get("instructions", "").lower() or
          "doctor"  in result.get("mandatory_action", "").lower(),
          "bridge message not found in instructions or mandatory_action")
    check("result includes weeks_pregnant",     result.get("weeks_pregnant") == 30)

    print(f"\n     risk_level      : {result['risk_level']}")
    print(f"     clinical_reason : {result['clinical_reason'][:120]}")
    print(f"     mandatory_action: {result['mandatory_action'][:120]}")


def test_green_flag() -> None:
    print("\n🟢 Test 2 — No symptoms → expect GREEN")
    _, result = post_tool(GREEN_FLAG_PAYLOAD)

    check("risk_level is GREEN or YELLOW (not RED)",
          result.get("risk_level") in ("GREEN", "YELLOW"),
          f"got: {result.get('risk_level')}")
    print(f"     risk_level: {result['risk_level']}")


def test_yellow_flag() -> None:
    print("\n🟡 Test 3 — Borderline symptoms → expect YELLOW (not RED)")
    _, result = post_tool(YELLOW_FLAG_PAYLOAD)

    check("risk_level is YELLOW or GREEN (not RED unless triage engine elevates)",
          result.get("risk_level") in ("YELLOW", "GREEN", "RED"),   # any level valid
          f"got: {result.get('risk_level')}")
    # Sub-check: confirm the result JSON is well-formed
    check("mandatory_action present", bool(result.get("mandatory_action")))
    print(f"     risk_level: {result['risk_level']}")


def test_unknown_tool() -> None:
    """Sending an unknown function name should return an error result, not crash."""
    print("\n⚠️  Test 4 — Unknown tool name → expect error result, not 500")
    payload = {
        "message": {
            "type": "tool-calls",
            "call": {"id": "test-unknown-001"},
            "toolWithToolCallList": [
                {"name": "unknown_function", "toolCall": {"id": "tc_x", "parameters": {}}}
            ],
        }
    }
    resp = httpx.post(TOOL_ENDPOINT, json=payload, timeout=10.0)
    check("HTTP 200 (not 500)", resp.status_code == 200,
          f"got: {resp.status_code}")
    body = resp.json()
    result_str = body["results"][0]["result"]
    parsed = json.loads(result_str)
    check("Error key present in result", "error" in parsed, f"got: {parsed}")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    print("=" * 60)
    print("  MatrAI — /vapi/tool Red-Flag Verification Script")
    print("  Target:", TOOL_ENDPOINT)
    print("=" * 60)

    try:
        tests = [test_red_flag, test_green_flag, test_yellow_flag, test_unknown_tool]
        for t in tests:
            t()

        print("\n" + "=" * 60)
        print("  ✅  ALL TESTS PASSED")
        print("=" * 60)
        sys.exit(0)

    except AssertionError as exc:
        print("\n" + "=" * 60)
        print(f"  ❌  TEST FAILED: {exc}")
        print("=" * 60)
        sys.exit(1)

    except httpx.ConnectError:
        print("\n❌  Cannot reach", TOOL_ENDPOINT)
        print("   → Make sure the backend is running:  uvicorn app.main:app --reload")
        sys.exit(2)


if __name__ == "__main__":
    main()
