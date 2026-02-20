"""
scripts/test_prompt.py
-----------------------
Verifies that build_system_prompt() correctly injects triage results
and that all safety constraints are present in the generated prompt.

Usage:
    python scripts/test_prompt.py

Expected output:
    - Full RED prompt printed to console
    - ✓ assertion checks for every safety rule
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make app/ importable from the scripts/ directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.prompts import (
    INITIAL_SYSTEM_PROMPT,
    build_system_prompt,
    green_prompt,
    red_alert_prompt,
    yellow_alert_prompt,
)

DIVIDER = "=" * 70


def check(label: str, condition: bool) -> None:
    status = "✓" if condition else "✗ FAIL"
    print(f"  [{status}] {label}")
    if not condition:
        sys.exit(1)


# ---------------------------------------------------------------------------
# 1. Print the RED prompt (main dev verification)
# ---------------------------------------------------------------------------
print(DIVIDER)
print("  TEST: build_system_prompt('RED', mandatory_action, clinical_reason)")
print(DIVIDER)

red = build_system_prompt(
    risk_level="RED",
    mandatory_action="Hospital turant jaaiye. 108 par call karein.",
    clinical_reason="Bleeding reported — possible antepartum haemorrhage.",
)

print(red)

# ---------------------------------------------------------------------------
# 2. Safety constraint assertions
# ---------------------------------------------------------------------------
print()
print(DIVIDER)
print("  SAFETY CONSTRAINT CHECKS")
print(DIVIDER)

# Rule 1 — No medicine
check("No-medicine constraint present", "KABHI BHAI DAWAI MAT BATAO" in red)

# Rule 2 — Mandatory action present and injected verbatim
check("Mandatory action injected",     "Hospital turant jaaiye" in red)
check("Negative constraint present",   "Do NOT say" in red or "NEGATIVE CONSTRAINT" in red)
check("Direct command language rule",  "ABHI hospital jaayein" in red)

# Rule 3 — 108 emergency
check("108 emergency rule present",    "108" in red)

# Rule 4 — No diagnosis
check("No-diagnosis rule present",     "DON'T DIAGNOSE" in red)

# Vocabulary guide
check("Vocabulary guide: sar dard",    "sar dard" in red)
check("Vocabulary guide: BP zyada",    "BP zyada hona" in red)
check("Vocabulary guide: pair sujan",  "pair sujan" in red)

# Cultural
check("'Behen' honorific present",     "Behen" in red)
check("'Namaste' greeting present",    "Namaste" in red)

# Quiet caller
check("Quiet caller handler present",  "5 second" in red)

# Weeks → Months
check("Weeks→months conversion rule",  "MAHINE MEIN BOLEIN" in red or "mahina" in red.lower())
check("Anti-weeks constraint",         "KABHI MAT BOLEIN" in red)

# Triage result block injected
check("Triage result block present",   "CURRENT TRIAGE RESULT" in red)
check("Risk level RED injected",       "Risk Level      : RED" in red)
check("Clinical reason injected",      "Bleeding reported" in red)

# ---------------------------------------------------------------------------
# 3. INITIAL prompt (no triage) should NOT have the triage block
# ---------------------------------------------------------------------------
print()
print(DIVIDER)
print("  INITIAL PROMPT CHECKS (no triage injected)")
print(DIVIDER)

check("INITIAL_SYSTEM_PROMPT loads",        len(INITIAL_SYSTEM_PROMPT) > 500)
check("No triage block in initial prompt",  "CURRENT TRIAGE RESULT" not in INITIAL_SYSTEM_PROMPT)
check("All safety rules in initial prompt", "KABHI BHAI DAWAI MAT BATAO" in INITIAL_SYSTEM_PROMPT)

# ---------------------------------------------------------------------------
# 4. Convenience wrappers
# ---------------------------------------------------------------------------
print()
print(DIVIDER)
print("  CONVENIENCE WRAPPER CHECKS")
print(DIVIDER)

yellow = yellow_alert_prompt("ANM se aaj milein.", "Fever — possible malaria.")
green  = green_prompt("ANC check-up time par karwayein.", "No danger signs.")

check("RED wrapper works",    "CURRENT TRIAGE RESULT" in red_alert_prompt("test", "reason"))
check("YELLOW wrapper works", "YELLOW" in yellow)
check("GREEN wrapper works",  "GREEN" in green)
check("YELLOW action injected", "ANM se aaj milein" in yellow)
check("GREEN action injected",  "ANC check-up" in green)

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
print()
print(DIVIDER)
print("  ALL CHECKS PASSED ✓")
print(DIVIDER)
