from haccp.services.media import TranscriptionService


def test_normalize_audio_suffix_from_filename() -> None:
    service = TranscriptionService()
    assert service._normalize_audio_suffix("voice.ogg") == ".ogg"
    assert service._normalize_audio_suffix("voice", mime_type="audio/ogg") == ".ogg"
    assert service._normalize_audio_suffix("recording", mime_type="audio/mpeg") == ".mp3"
    assert service._normalize_audio_suffix("recording", mime_type="audio/wav") == ".wav"


def test_transcribe_retries_on_error(monkeypatch) -> None:
    call_count = {"n": 0}

    def fake_create(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise RuntimeError("temporary failure")
        class FakeResult:
            text = "транскрипция"
        return FakeResult()

    class FakeAudioClient:
        def __init__(self, *args, **kwargs):
            self.audio = self
            self.transcriptions = self

        def create(self, *args, **kwargs):
            return fake_create(*args, **kwargs)

    monkeypatch.setattr(TranscriptionService, "__init__", lambda self: setattr(self, "client", FakeAudioClient()))
    service = TranscriptionService()

    text = service.transcribe(b"dummy", filename="voice.ogg")
    assert text == "транскрипция"
    assert call_count["n"] == 3
