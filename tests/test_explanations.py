"""Explanations cite only evidence that exists."""

import pytest

from gridsignal.config import load_settings
from gridsignal.explain.evidence import bundle_for_event
from gridsignal.explain.llm_provider import UnsupportedClaimError, validate_claims
from gridsignal.explain.templates import explain_anomaly
from gridsignal.services.pipeline import run_demo


def test_template_evidence_ids_exist() -> None:
    result = run_demo(load_settings(_env_file=None, data_mode="demo"))
    assert result.explanations
    event = result.anomalies.iloc[0]
    items = bundle_for_event(event, result.observations)
    explanation = explain_anomaly(event.to_dict(), items)
    allowed = {item.evidence_id for item in items}
    assert set(explanation.evidence_ids) <= allowed
    assert explanation.facts
    assert explanation.hypotheses
    assert "SYNTHETIC" in explanation.text


def test_llm_claims_must_use_known_ids() -> None:
    ok = validate_claims(
        {"subject_id": "evt-1", "claims": [{"text": "Load was 1 MW.", "evidence_ids": ["ev-1"]}]},
        {"ev-1"},
    )
    assert ok.evidence_ids == ["ev-1"]
    with pytest.raises(UnsupportedClaimError):
        validate_claims(
            {"claims": [{"text": "Invented.", "evidence_ids": ["ev-missing"]}]},
            {"ev-1"},
        )
