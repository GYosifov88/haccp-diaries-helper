from haccp.graph.nodes import pending
from haccp.models.state import ExtractedEntry


def test_llm_fallback_is_used_when_no_regex(monkeypatch) -> None:
    entry = ExtractedEntry(entry_type="incoming_goods")

    def fake_llm(text, entry_type):
        return {"expiry_date": "01.01.2027", "supplier": "LLM Vendor"}

    monkeypatch.setattr(pending, "_invoke_llm_followup", lambda t, e: fake_llm(t, e))

    updated = pending.continue_pending_entry(entry, "продължи")

    assert updated.expiry_date == "01.01.2027"
    assert updated.supplier == "LLM Vendor"
