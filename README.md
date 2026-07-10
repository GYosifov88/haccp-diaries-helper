# HACCP Diaries Helper

This project is a LangGraph-based rewrite of an n8n Telegram workflow for HACCP diary entry handling.

## What it does
- Receives Telegram text and media input.
- Classifies diary entry type.
- Extracts structured entry data.
- Validates required fields.
- Writes entries to Google Sheets.
- Stores incomplete follow-up states for later continuation.

## Quick start
1. Create a `.env` file from `.env.example`.
2. Install dependencies:
   `pip install -e .[dev]`
3. Run the sample workflow:
   `python -m haccp.main`
