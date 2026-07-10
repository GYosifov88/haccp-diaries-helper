from haccp.graph.nodes import pending
from haccp.models.state import ExtractedEntry
import json


def test_llm_cache_prevents_duplicate_calls(monkeypatch):
    # monkeypatch the low-level call to count invocations
    calls = {"n": 0}

    def fake_call(prompt: str):
        calls["n"] += 1
        return json.dumps({"expiry_date": "02.02.2028"})

    monkeypatch.setattr(pending, "_call_llm_raw", fake_call)
    pending._clear_llm_cache()

    entry = ExtractedEntry(entry_type="incoming_goods")
    # First call should invoke the fake LLM once
    res1 = pending._invoke_llm_followup("продължи", "incoming_goods")
    assert res1["expiry_date"] == "02.02.2028"
    assert calls["n"] == 1

    # Second call with same input should be cached and not increase calls
    res2 = pending._invoke_llm_followup("продължи", "incoming_goods")
    assert res2["expiry_date"] == "02.02.2028"
    assert calls["n"] == 1

    # Clearing cache forces another call
    pending._clear_llm_cache()
    res3 = pending._invoke_llm_followup("продължи", "incoming_goods")
    assert calls["n"] == 2
