from haccp.graph.nodes.extraction import extract_entry
from haccp.models.state import ExtractedEntry


def test_voice_transcription_merges_text(monkeypatch):
    # fake transcription service
    def fake_transcribe(self, audio_bytes, filename="voice.ogg"):
        return "Доставчик Стар, срок на годност 10.07.2026"

    from haccp.services.media import TranscriptionService

    monkeypatch.setattr(TranscriptionService, "transcribe", fake_transcribe)

    state = {
        "raw_text": None,
        "input_text": None,
        "input_kind": "voice",
        "file_bytes": b"audio-bytes",
        "file_mime": "audio/ogg",
        "user": None,
        "entry_type": "incoming_goods",
    }

    updated = extract_entry(state)
    entry = updated.get("extracted")
    assert isinstance(entry, ExtractedEntry)
    assert entry.supplier is not None
    assert entry.expiry_date is not None
    assert "10.07.2026" in str(entry.expiry_date)
