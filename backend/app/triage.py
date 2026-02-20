"""
app/triage.py
-------------
Obstetric risk triage engine based on the Government of India's
Pradhan Mantri Surakshit Matritva Abhiyan (PMSMA) guidelines.

Reference:
  - PMSMA Operational Guidelines, MoHFW, GoI (2016, updated 2021)
  - Janani Suraksha Yojana (JSY) danger sign protocol
  - FOGSI / WHO Safe Motherhood recommendations adopted by NHM India

Risk levels (evaluated in priority order):
  RED    → Emergency / Life-threatening — immediate hospital referral
  YELLOW → High-risk / Urgent — must see a health provider within 24 h
  GREEN  → Low-risk — routine ANC follow-up advised

Usage:
    from app.triage import evaluate_risk

    result = evaluate_risk({
        "bleeding": "heavy",
        "convulsions": True,
        "fever": True,
    })
    # → {"risk_level": "RED", "mandatory_action": "...", "clinical_reason": "..."}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Internal data model
# ---------------------------------------------------------------------------

@dataclass
class _TriageRule:
    """Represents a single clinical triage rule."""
    risk_level: str          # "RED" | "YELLOW" | "GREEN"
    symptom_key: str         # key in the symptoms dict
    trigger_value: Any       # value that activates this rule
    mandatory_action: str    # what the patient must do
    clinical_reason: str     # PMSMA-sourced clinical justification


# ---------------------------------------------------------------------------
# PMSMA Rule Table
# Rules are evaluated in order; the FIRST match wins (highest priority first).
# ---------------------------------------------------------------------------

_RULES: list[_TriageRule] = [
    # ======================================================================
    # RED FLAGS — Emergency (PMSMA Section 4: Danger Signs in Pregnancy)
    # ======================================================================
    _TriageRule(
        risk_level="RED",
        symptom_key="bleeding",
        trigger_value="heavy",
        mandatory_action=(
            "Go to the nearest government hospital or PHC immediately. "
            "Call 108 (ambulance) if unable to travel. Do NOT wait."
        ),
        clinical_reason=(
            "Heavy antepartum or postpartum haemorrhage is a leading direct cause "
            "of maternal mortality in India (SRS 2020). Per PMSMA danger-sign protocol, "
            "heavy vaginal bleeding warrants immediate obstetric intervention — "
            "possible placenta praevia, placental abruption, or uterine rupture."
        ),
    ),
    _TriageRule(
        risk_level="RED",
        symptom_key="convulsions",
        trigger_value=True,
        mandatory_action=(
            "Call 108 immediately. Lay the patient on her left side. "
            "Do NOT give anything by mouth. Reach a FIRST REFERRAL UNIT (FRU) at once."
        ),
        clinical_reason=(
            "Convulsions in pregnancy indicate eclampsia until proven otherwise — "
            "a hypertensive emergency with high maternal and perinatal mortality risk. "
            "PMSMA and NHM protocols mandate emergency magnesium sulphate therapy "
            "and immediate referral to an FRU with Comprehensive Emergency Obstetric "
            "Care (CEmOC) capability."
        ),
    ),
    _TriageRule(
        risk_level="RED",
        symptom_key="severe_headache",
        trigger_value=True,
        mandatory_action=(
            "Seek emergency care at a government hospital immediately. "
            "Monitor blood pressure if possible. Call 108 if BP is ≥ 160/110 mmHg."
        ),
        clinical_reason=(
            "Severe headache in pregnancy — especially in the third trimester — "
            "is a cardinal warning sign of pre-eclampsia / imminent eclampsia per "
            "PMSMA and WHO ANC guidelines (2016). It may precede convulsions by minutes "
            "to hours. Immediate BP assessment and anti-hypertensive + MgSO4 therapy "
            "at an FRU is mandatory."
        ),
    ),
    _TriageRule(
        risk_level="RED",
        symptom_key="fetal_movement",
        trigger_value="decreased",
        mandatory_action=(
            "Go to the nearest health facility today for a fetal well-being check "
            "(Non-Stress Test or kick-count assessment). Do not delay overnight."
        ),
        clinical_reason=(
            "Decreased or absent fetal movements (fewer than 10 movements in 2 hours) "
            "is a recognised danger sign of foetal distress / intrauterine foetal death "
            "per PMSMA screening criteria and RCOG guideline (adopted by NHM India). "
            "Immediate cardiotocography (CTG) or Doppler assessment is required."
        ),
    ),

    # ======================================================================
    # YELLOW FLAGS — High-Risk / Urgent (PMSMA Section 5: High-Risk Conditions)
    # ======================================================================
    _TriageRule(
        risk_level="YELLOW",
        symptom_key="fever",
        trigger_value=True,
        mandatory_action=(
            "Visit the nearest Primary Health Centre (PHC) or Sub-Centre within 24 hours. "
            "Stay hydrated. Carry your ANC card."
        ),
        clinical_reason=(
            "Fever during pregnancy raises concern for malaria, urinary tract infection, "
            "or chorioamnionitis — all associated with preterm labour and foetal loss "
            "per PMSMA high-risk categorisation. Malaria in pregnancy is notifiable "
            "under NHM guidelines and requires prompt blood-smear or RDT testing."
        ),
    ),
    _TriageRule(
        risk_level="YELLOW",
        symptom_key="swelling_feet",
        trigger_value=True,
        mandatory_action=(
            "Visit your ASHA worker or ANM today for blood pressure measurement. "
            "If BP > 140/90 mmHg, proceed to PHC immediately. Rest with feet elevated."
        ),
        clinical_reason=(
            "Oedema of the feet and ankles, particularly when sudden or severe, "
            "is a high-risk indicator for gestational hypertension / pre-eclampsia "
            "under PMSMA screening. Per JSY/ASHA guidelines, BP must be checked "
            "and proteinuria ruled out. Generalised oedema with proteinuria meets "
            "diagnostic criteria for pre-eclampsia."
        ),
    ),
    _TriageRule(
        risk_level="YELLOW",
        symptom_key="abdominal_pain",
        trigger_value="mild",
        mandatory_action=(
            "Contact your ANM or ASHA worker within 24 hours. "
            "Note the frequency, duration, and location of pain. "
            "Go to a PHC if pain worsens or becomes rhythmic."
        ),
        clinical_reason=(
            "Mild abdominal pain can signal preterm uterine contractions, urinary "
            "tract infection, or early placental abruption. PMSMA ANC visit checklists "
            "require evaluation of abdominal pain to exclude threatened preterm labour "
            "(< 37 weeks) or round-ligament pain. Rhythmic or worsening pain upgrades "
            "the risk to RED immediately."
        ),
    ),
]

# Green-level fallback (no red/yellow flags triggered)
_GREEN_RESULT: dict = {
    "risk_level": "GREEN",
    "mandatory_action": (
        "Continue routine Antenatal Care (ANC). Attend your next scheduled PMSMA "
        "check-up (9th, 15th, or 21st of each month at a government facility). "
        "Take your prescribed IFA tablets daily and ensure TT vaccination is up to date."
    ),
    "clinical_reason": (
        "No danger signs or high-risk indicators detected based on reported symptoms. "
        "Low-risk status per PMSMA triage criteria. Regular ANC visits (minimum 4 per "
        "WHO / GoI recommendation), iron-folic acid supplementation, and birth "
        "preparedness planning should continue as advised by your ANM/ASHA."
    ),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_risk(symptoms: dict) -> dict:
    """
    Evaluate obstetric risk based on reported symptoms using PMSMA guidelines.

    The function applies rules in strict priority order (RED before YELLOW).
    The first matching rule determines the outcome — subsequent rules are
    not evaluated (short-circuit).  A GREEN result is returned only when
    no RED or YELLOW rule is triggered.

    Args:
        symptoms (dict): A flat dictionary of symptom keys and their values.
            Recognised keys and expected value types:

            Key                 | Type / Values
            --------------------|----------------------------------
            bleeding            | str: 'none' | 'light' | 'heavy'
            convulsions         | bool
            severe_headache     | bool
            fetal_movement      | str: 'normal' | 'decreased' | 'absent'
            fever               | bool
            swelling_feet       | bool
            abdominal_pain      | str: 'none' | 'mild' | 'severe'

            Unknown keys are ignored; missing keys are treated as "not present"
            (i.e., they will not trigger any rule).

    Returns:
        dict: A result dictionary with three keys:
            {
                "risk_level":       "RED" | "YELLOW" | "GREEN",
                "mandatory_action": str,   # what the patient must do
                "clinical_reason":  str,   # PMSMA-based clinical justification
            }

    Examples:
        >>> evaluate_risk({"bleeding": "heavy"})
        {'risk_level': 'RED', 'mandatory_action': '...', 'clinical_reason': '...'}

        >>> evaluate_risk({"fever": True, "swelling_feet": True})
        {'risk_level': 'YELLOW', ...}   # first matching rule wins

        >>> evaluate_risk({"bleeding": "light"})
        {'risk_level': 'GREEN', ...}
    """
    if not isinstance(symptoms, dict):
        raise TypeError(
            f"symptoms must be a dict, got {type(symptoms).__name__!r}"
        )

    matched_red: _TriageRule | None = None
    matched_yellow: _TriageRule | None = None

    for rule in _RULES:
        symptom_value = symptoms.get(rule.symptom_key)
        if symptom_value == rule.trigger_value:
            if rule.risk_level == "RED":
                # Return immediately — RED is the highest severity
                return _build_result(rule)
            elif rule.risk_level == "YELLOW" and matched_yellow is None:
                # Capture first yellow; keep scanning for possible RED
                matched_yellow = rule

    if matched_yellow:
        return _build_result(matched_yellow)

    return dict(_GREEN_RESULT)


def _build_result(rule: _TriageRule) -> dict:
    """Construct the triage result dict from a matched rule."""
    return {
        "risk_level": rule.risk_level,
        "mandatory_action": rule.mandatory_action,
        "clinical_reason": rule.clinical_reason,
    }
