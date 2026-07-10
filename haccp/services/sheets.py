from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import gspread
from google.oauth2.service_account import Credentials

from haccp.config import DiaryConfig, get_diaries, get_settings
from haccp.models.state import ExtractedEntry, InvoiceItem, MissingField, WrittenEntry

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

UNKNOWN_VALUES = {"", "неизвестна", "неизвестен", "unknown", "n/a"}


class SheetsService:
    """Single dynamic Google Sheets writer for all diary types."""

    def __init__(self) -> None:
        settings = get_settings()
        creds = Credentials.from_service_account_file(
            settings.google_sheets_credentials_path,
            scopes=SCOPES,
        )
        self.client = gspread.authorize(creds)
        self.spreadsheet = self.client.open_by_key(settings.google_spreadsheet_id)
        self.timezone = ZoneInfo(settings.timezone)
        self.diaries = get_diaries()

    def _now(self) -> datetime:
        return datetime.now(self.timezone)

    def _format_timestamp(self) -> str:
        return self._now().strftime("%d.%m.%Y %H:%M:%S")

    def _format_date(self, entry: ExtractedEntry) -> str:
        if entry.date:
            return entry.date
        return self._now().strftime("%d.%m.%Y")

    def _format_time(self, entry: ExtractedEntry) -> str:
        if entry.time:
            return entry.time
        return self._now().strftime("%H:%M")

    def _build_row(
        self,
        entry: ExtractedEntry,
        diary: DiaryConfig,
        *,
        entry_id: str,
        signature: str,
        item: InvoiceItem | None = None,
    ) -> dict[str, Any]:
        data = entry.to_row_dict()
        if item is not None:
            data["product"] = item.product
            data["quantity"] = item.quantity
            data["unit"] = item.unit
            data["temperature"] = item.temperature
            data["expiry_date"] = item.expiry_date
            data["package_condition"] = item.package_condition
            data["decision"] = item.decision

        data["entry_id"] = entry_id
        data["date"] = self._format_date(entry)
        data["time"] = self._format_time(entry)
        data["signature"] = signature or data.get("signature") or ""
        data["timestamp"] = self._format_timestamp()

        if entry.entry_type == "incoming_goods" and data.get("quantity") is not None:
            unit = data.get("unit") or "бр"
            data["quantity"] = f"{data.get('quantity')} {unit}".strip()

        row: dict[str, Any] = {}
        for field, column in diary.columns.items():
            if column in row:
                continue
            value = data.get(field)
            if value is not None and value != "":
                row[column] = value
        return row

    def _find_missing(
        self, entry: ExtractedEntry, diary: DiaryConfig, row: dict[str, Any]
    ) -> list[MissingField]:
        missing: list[MissingField] = []
        for field in diary.required_fields:
            column = diary.columns.get(field, field)
            value = row.get(column) or getattr(entry, field, None)
            if value is None or str(value).strip().lower() in UNKNOWN_VALUES:
                missing.append(MissingField(field=field, label=column))
        return missing

    def append_entry(
        self,
        entry: ExtractedEntry,
        *,
        signature: str,
        entry_id: str | None = None,
    ) -> list[WrittenEntry]:
        if entry.entry_type == "unknown":
            raise ValueError("Cannot write unknown entry type")

        diary = self.diaries[entry.entry_type]
        worksheet = self._get_worksheet(diary.sheet)
        entry_id = entry_id or str(int(self._now().timestamp() * 1000))

        rows: list[dict[str, Any]] = []
        if entry.entry_type == "incoming_goods" and diary.supports_invoice_items and entry.items:
            for item in entry.items:
                rows.append(
                    self._build_row(
                        entry,
                        diary,
                        entry_id=entry_id,
                        signature=signature,
                        item=item,
                    )
                )
        else:
            rows.append(self._build_row(entry, diary, entry_id=entry_id, signature=signature))

        headers = worksheet.row_values(1)
        if not headers:
            headers = list(rows[0].keys())
            worksheet.append_row(headers, value_input_option="USER_ENTERED")

        written_entries: list[WrittenEntry] = []
        for row in rows:
            ordered = [row.get(h, "") for h in headers]
            worksheet.append_row(ordered, value_input_option="USER_ENTERED")
            row_number = len(worksheet.get_all_values())
            missing = self._find_missing(entry, diary, row)
            written_entries.append(
                WrittenEntry(
                    entry_id=entry_id,
                    entry_type=entry.entry_type,
                    sheet_name=diary.sheet,
                    row_number=row_number,
                    data=row,
                    missing=missing,
                )
            )

        return written_entries

    def update_row(
        self,
        *,
        sheet_name: str,
        row_number: int,
        updates: dict[str, Any],
    ) -> None:
        worksheet = self._get_worksheet(sheet_name)
        headers = worksheet.row_values(1)
        for column, value in updates.items():
            if column not in headers:
                continue
            col_idx = headers.index(column) + 1
            worksheet.update_cell(row_number, col_idx, value)

    def update_fields_by_entry_type(
        self,
        entry_type: str,
        row_number: int,
        field_updates: dict[str, Any],
    ) -> None:
        diary = self.diaries[entry_type]
        column_updates = {
            diary.columns[field]: value
            for field, value in field_updates.items()
            if field in diary.columns
        }
        self.update_row(
            sheet_name=diary.sheet,
            row_number=row_number,
            updates=column_updates,
        )

    def _get_worksheet(self, sheet_name: str):
        try:
            return self.spreadsheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound as exc:
            raise ValueError(f"Sheet not found: {sheet_name}") from exc
