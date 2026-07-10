# n8n to LangGraph migration map

## Original workflow intent
The attached n8n workflow handles a Telegram-driven HACCP diary assistant:

1. Receive Telegram messages or edited messages.
2. Resolve the Telegram user and determine whether they are allowed.
3. Handle text, voice, photos, or documents.
4. For voice, transcribe audio.
5. For photos/documents, extract OCR text.
6. Build a dynamic prompt for the LLM and classify the diary type.
7. Extract structured diary data in JSON.
8. Append the result to the correct Google Sheet.
9. Ask follow-up questions when a required field is missing.

## Current implementation plan
The new LangGraph version mirrors this sequence with explicit nodes:

- `resolve_user` -> validate Telegram identity and signature.
- `classify_entry_type` -> infer the diary type from the message.
- `extract_entry` -> create a structured `ExtractedEntry` from text or OCR content.
- `validate_entry` -> ensure required fields are present.
- `write_entry` -> append the result to Google Sheets.
- `finalize` -> return a human-friendly confirmation and any follow-up questions.

## Mapping notes
- The n8n `Build Dynamic Context` node becomes the LangGraph state initializer plus prompt-building logic.
- The `Resolve User` node becomes a graph node that reads the Telegram user from config.
- The `OCR Document` and `Transcribe a recording` nodes map to media services already present in the repository.
- The Google Sheets append nodes map to the existing `SheetsService`.
- The pending follow-up logic maps to the existing SQLite pending-store service.
