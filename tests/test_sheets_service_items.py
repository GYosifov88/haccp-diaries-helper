from zoneinfo import ZoneInfo
from types import SimpleNamespace

from haccp.config import DiaryConfig
from haccp.models.state import ExtractedEntry, InvoiceItem
from haccp.services.sheets import SheetsService


class FakeWorksheet:
    def __init__(self) -> None:
        self.rows: list[list[str]] = []

    def row_values(self, row_number: int) -> list[str]:
        if row_number == 1 and self.rows:
            return self.rows[0]
        return []

    def append_row(self, values: list[str], value_input_option: str = "USER_ENTERED") -> None:
        self.rows.append([str(value) for value in values])

    def get_all_values(self) -> list[list[str]]:
        return self.rows


class FakeSpreadsheet:
    def __init__(self, worksheet: FakeWorksheet) -> None:
        self._worksheet = worksheet

    def worksheet(self, sheet_name: str) -> FakeWorksheet:
        return self._worksheet


def test_append_entry_writes_each_invoice_item(monkeypatch) -> None:
    fake_worksheet = FakeWorksheet()

    def fake_init(self):
        self.client = None
        self.spreadsheet = FakeSpreadsheet(fake_worksheet)
        self.timezone = ZoneInfo("UTC")
        self.diaries = {
            "incoming_goods": DiaryConfig(
                label="входящ контрол",
                sheet="Дневник за входящ контрол",
                required_fields=[
                    "supplier",
                    "product",
                    "temperature",
                    "expiry_date",
                    "package_condition",
                    "documents",
                    "decision",
                ],
                supports_invoice_items=True,
                columns={
                    "entry_id": "entry_id",
                    "date": "Дата",
                    "supplier": "Доставчик",
                    "product": "Продукт",
                    "quantity": "Количество",
                    "temperature": "Температура при приемане",
                    "expiry_date": "Срок на годност",
                    "package_condition": "Състояние на опаковката",
                    "documents": "Документи (фактура/стокова разписка)",
                    "decision": "Решение (прието/отказано)",
                    "note": "Забележка",
                    "signature": "Подпис",
                    "timestamp": "timestamp",
                },
            )
        }

    monkeypatch.setattr(SheetsService, "__init__", fake_init)

    service = SheetsService()
    entry = ExtractedEntry(
        entry_type="incoming_goods",
        supplier="Тестов доставчик",
        signature="Иван",
        items=[
            InvoiceItem(
                product="мляко",
                quantity=10,
                unit="л",
                temperature="3",
                expiry_date="10.07.2026",
                package_condition="добра",
                decision="прието",
            ),
            InvoiceItem(
                product="хляб",
                quantity=5,
                unit="бр",
                temperature="неизвестна",
                expiry_date="15.08.2026",
                package_condition="добра",
                decision="прието",
            ),
        ],
    )

    written_entries = service.append_entry(entry, signature="Иван")

    assert len(written_entries) == 2
    assert fake_worksheet.rows[0][0] == "entry_id"
    assert "Продукт" in fake_worksheet.rows[0]
    assert fake_worksheet.rows[1][fake_worksheet.rows[0].index("Продукт")] == "мляко"
    assert fake_worksheet.rows[2][fake_worksheet.rows[0].index("Продукт")] == "хляб"
    assert written_entries[0].row_number == 2
    assert written_entries[1].row_number == 3
    assert "10 л" in fake_worksheet.rows[1][fake_worksheet.rows[0].index("Количество")]
    assert "5 бр" in fake_worksheet.rows[2][fake_worksheet.rows[0].index("Количество")]
