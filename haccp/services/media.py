from __future__ import annotations

import base64
import io
import tempfile
import time
from pathlib import Path

from langchain_openai import ChatOpenAI
from openai import OpenAI

from haccp.config import get_settings

OCR_PROMPT = """You are an OCR assistant. Extract ALL text from this invoice/document image.

Focus on:
- Supplier name (доставчик/получател/фирма)
- Product names (наименование на стоката)
- Quantities (количество/кол-во)
- Prices (цена/стойност)
- Invoice number (фактура №)
- Date (дата)
- Expiry dates (срок на годност) if present

Return the complete raw text exactly as it appears.
Preserve all numbers, dates, names, and codes.
Do NOT summarize. Return ALL visible text."""


class OCRService:
    def __init__(self) -> None:
        settings = get_settings()
        self.model = settings.openai_model
        self.llm = ChatOpenAI(model=self.model, temperature=0)
        self.client = OpenAI(api_key=settings.openai_api_key)

    def extract_text(self, file_bytes: bytes, mime_type: str = "image/jpeg") -> str:
        b64 = base64.b64encode(file_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{b64}"

        response = self.llm.invoke(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": OCR_PROMPT},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ]
        )
        return str(response.content).strip()


class TranscriptionService:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = OpenAI(api_key=settings.openai_api_key)

    def transcribe(self, audio_bytes: bytes, filename: str = "voice.ogg", mime_type: str | None = None) -> str:
        suffix = self._normalize_audio_suffix(filename, mime_type)
        max_attempts = 3
        base_delay = 0.5

        for attempt in range(1, max_attempts + 1):
            try:
                with tempfile.NamedTemporaryFile(suffix=f"_{suffix}", delete=False) as tmp:
                    tmp.write(audio_bytes)
                    tmp.flush()
                    tmp_path = tmp.name

                with open(tmp_path, "rb") as audio_file:
                    result = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language="bg",
                    )

                Path(tmp_path).unlink(missing_ok=True)
                return result.text.strip()
            except Exception:
                if attempt == max_attempts:
                    Path(tmp_path).unlink(missing_ok=True)
                    raise
                Path(tmp_path).unlink(missing_ok=True)
                time.sleep(base_delay * (2 ** (attempt - 1)))

    def _normalize_audio_suffix(self, filename: str, mime_type: str | None = None) -> str:
        path = Path(filename)
        if path.suffix:
            return path.suffix

        if mime_type == "audio/ogg":
            return ".ogg"
        if mime_type == "audio/mpeg" or mime_type == "audio/mp3":
            return ".mp3"
        if mime_type == "audio/wav":
            return ".wav"
        if mime_type == "audio/webm":
            return ".webm"
        return ".ogg"
