"""
tests/test_triage.py
--------------------
Unit tests for the PMSMA obstetric triage engine (app/triage.py).

Test coverage:
  1. RED  — Heavy bleeding (antepartum haemorrhage)
  2. RED  — Convulsions (eclampsia / imminent eclampsia)
  3. YELLOW — Fever (infection risk)
  4. YELLOW — RED flag beats concurrent YELLOW flag (priority ordering)
  5. GREEN  — No recognised symptoms reported

Run with:
    pytest tests/test_triage.py -v
"""

import pytest

from app.triage import evaluate_risk


# ===========================================================================
# Helpers
# ===========================================================================

def _assert_result(result: dict, expected_level: str) -> None:
    """Assert the three required keys exist and risk_level matches."""
    assert "risk_level" in result, "Result must contain 'risk_level'"
    assert "mandatory_action" in result, "Result must contain 'mandatory_action'"
    assert "clinical_reason" in result, "Result must contain 'clinical_reason'"
    assert result["risk_level"] == expected_level, (
        f"Expected risk_level={expected_level!r}, got {result['risk_level']!r}"
    )
    assert isinstance(result["mandatory_action"], str) and len(result["mandatory_action"]) > 0, (
        "mandatory_action must be a non-empty string"
    )
    assert isinstance(result["clinical_reason"], str) and len(result["clinical_reason"]) > 0, (
        "clinical_reason must be a non-empty string"
    )


# ===========================================================================
# Test Case 1 — RED: Heavy bleeding
# ===========================================================================

class TestRedFlagBleeding:
    """Antepartum haemorrhage is a direct cause of maternal mortality (PMSMA)."""

    def test_heavy_bleeding_returns_red(self):
        result = evaluate_risk({"bleeding": "heavy"})
        _assert_result(result, "RED")

    def test_heavy_bleeding_action_mentions_hospital(self):
        result = evaluate_risk({"bleeding": "heavy"})
        action = result["mandatory_action"].lower()
        assert "hospital" in action or "108" in action, (
            "mandatory_action for heavy bleeding must direct patient to a hospital or call 108"
        )

    def test_light_bleeding_is_not_red(self):
        """Light bleeding is not in the RED rule set — should not trigger RED."""
        result = evaluate_risk({"bleeding": "light"})
        assert result["risk_level"] != "RED", (
            "Light bleeding should NOT be flagged RED"
        )


# ===========================================================================
# Test Case 2 — RED: Convulsions (eclampsia)
# ===========================================================================

class TestRedFlagConvulsions:
    """Convulsions = eclampsia until proven otherwise; immediate CEmOC referral needed."""

    def test_convulsions_true_returns_red(self):
        result = evaluate_risk({"convulsions": True})
        _assert_result(result, "RED")

    def test_convulsions_false_does_not_trigger(self):
        result = evaluate_risk({"convulsions": False})
        assert result["risk_level"] != "RED", (
            "convulsions=False must not produce a RED result"
        )

    def test_convulsions_action_mentions_108_or_emergency(self):
        result = evaluate_risk({"convulsions": True})
        action = result["mandatory_action"].lower()
        assert "108" in action or "emergency" in action or "immediately" in action, (
            "mandatory_action for convulsions must reference emergency services or 108"
        )


# ===========================================================================
# Test Case 3 — YELLOW: Fever
# ===========================================================================

class TestYellowFlagFever:
    """Fever during pregnancy → malaria / UTI / chorioamnionitis risk (PMSMA high-risk)."""

    def test_fever_true_returns_yellow(self):
        result = evaluate_risk({"fever": True})
        _assert_result(result, "YELLOW")

    def test_fever_action_mentions_phc_or_24h(self):
        result = evaluate_risk({"fever": True})
        action = result["mandatory_action"].lower()
        assert "24" in action or "phc" in action or "health centre" in action, (
            "mandatory_action for fever must recommend visiting a PHC within 24 hours"
        )

    def test_fever_false_does_not_trigger(self):
        result = evaluate_risk({"fever": False})
        assert result["risk_level"] != "YELLOW" or result.get("clinical_reason", "") == "", (
            "fever=False should not trigger the fever YELLOW rule"
        )


# ===========================================================================
# Test Case 4 — Priority: RED overrides concurrent YELLOW
# ===========================================================================

class TestRedBeatsYellowPriority:
    """
    When both RED and YELLOW symptoms are reported simultaneously,
    the engine must return RED — highest severity always wins.
    """

    def test_bleeding_plus_fever_yields_red(self):
        result = evaluate_risk({"bleeding": "heavy", "fever": True})
        _assert_result(result, "RED")

    def test_convulsions_plus_swelling_yields_red(self):
        result = evaluate_risk({"convulsions": True, "swelling_feet": True})
        _assert_result(result, "RED")

    def test_severe_headache_plus_abdominal_pain_yields_red(self):
        result = evaluate_risk({"severe_headache": True, "abdominal_pain": "mild"})
        _assert_result(result, "RED")


# ===========================================================================
# Test Case 5 — GREEN: No recognised symptoms
# ===========================================================================

class TestGreenNoSymptoms:
    """No danger signs → low-risk; routine ANC follow-up advised."""

    def test_empty_dict_returns_green(self):
        result = evaluate_risk({})
        _assert_result(result, "GREEN")

    def test_no_matching_symptoms_returns_green(self):
        result = evaluate_risk({"bleeding": "none", "abdominal_pain": "none"})
        _assert_result(result, "GREEN")

    def test_green_action_mentions_anc(self):
        result = evaluate_risk({})
        action = result["mandatory_action"].lower()
        assert "anc" in action or "antenatal" in action or "pmsma" in action, (
            "GREEN mandatory_action should refer to routine ANC / PMSMA schedule"
        )

    def test_unknown_keys_ignored_returns_green(self):
        """Unrecognised symptom keys must be silently ignored."""
        result = evaluate_risk({"unknown_symptom": "xyz", "random_key": 99})
        _assert_result(result, "GREEN")


# ===========================================================================
# Edge-case / Robustness Tests
# ===========================================================================

class TestEdgeCases:
    """Guard the engine against unexpected inputs."""

    def test_non_dict_raises_type_error(self):
        with pytest.raises(TypeError):
            evaluate_risk("bleeding=heavy")  # type: ignore[arg-type]

    def test_none_value_does_not_trigger_rules(self):
        """None values for symptom keys must not accidentally match True/string rules."""
        result = evaluate_risk({"convulsions": None, "fever": None})
        assert result["risk_level"] == "GREEN"

    def test_result_keys_are_always_present(self):
        """Regardless of input, all three result keys must always be present."""
        for symptoms in [{}, {"bleeding": "heavy"}, {"fever": True}]:
            result = evaluate_risk(symptoms)
            assert set(result.keys()) == {"risk_level", "mandatory_action", "clinical_reason"}
