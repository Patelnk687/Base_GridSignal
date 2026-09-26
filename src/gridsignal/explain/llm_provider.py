"""Optional Ollama provider.

The model receives evidence ids and values only. Claims that cite an unknown
id are rejected. Secrets are not included in the prompt.
"""

from __future__ import annotations

import json
from typing import Any

import requests

from gridsignal.explain.evidence import EvidenceItem, Explanation
from gridsignal.explain.templates import explain_anomaly


class UnsupportedClaimError(ValueError):
    pass


def validate_claims(payload: dict[str, Any], allowed_ids: set[str]) -> Explanation:
    claims = payload.get("claims")
    if not isinstance(claims, list) or not claims:
        raise UnsupportedClaimError("LLM response did not include claims")
    facts: list[str] = []
    used: list[str] = []
    for claim in claims:
        text = str(claim.get("text", "")).strip()
        ids = claim.get("evidence_ids") or []
        if not text or not isinstance(ids, list) or not ids:
            raise UnsupportedClaimError("each claim needs text and evidence_ids")
        unknown = [item for item in ids if item not in allowed_ids]
        if unknown:
            raise UnsupportedClaimError(f"unsupported evidence ids: {unknown}")
        facts.append(text)
        used.extend(str(item) for item in ids)
    return Explanation(
        subject_id=str(payload.get("subject_id", "")),
        facts=facts,
        interpretation=["Model-written claim. Checked only for evidence-id membership."],
        hypotheses=[],
        evidence_ids=sorted(set(used)),
        provider="ollama",
        text=" ".join(facts),
    )


def explain_with_ollama(
    event: dict[str, object],
    items: list[EvidenceItem],
    *,
    base_url: str,
    model: str,
    timeout_s: float = 20.0,
    session: requests.Session | None = None,
) -> Explanation:
    allowed = {item.evidence_id for item in items}
    prompt = {
        "instruction": (
            "Write claims about this grid interval. Every claim must cite evidence_ids "
            "from the provided list. Do not invent numbers, causes, or sources. "
            "Return JSON with subject_id and claims: [{text, evidence_ids}]."
        ),
        "subject_id": event.get("event_id"),
        "evidence": [item.model_dump() for item in items],
    }
    http = session or requests.Session()
    try:
        response = http.post(
            base_url.rstrip("/") + "/api/chat",
            json={
                "model": model,
                "stream": False,
                "format": "json",
                "messages": [{"role": "user", "content": json.dumps(prompt)}],
            },
            timeout=timeout_s,
        )
        response.raise_for_status()
        content = response.json()["message"]["content"]
        parsed = json.loads(content)
        parsed.setdefault("subject_id", event.get("event_id"))
        return validate_claims(parsed, allowed)
    except (requests.RequestException, KeyError, json.JSONDecodeError, UnsupportedClaimError):
        fallback = explain_anomaly(event, items)
        fallback.interpretation.append(
            "Ollama was unavailable or returned an unsupported claim, so the template explanation is shown."
        )
        return fallback
