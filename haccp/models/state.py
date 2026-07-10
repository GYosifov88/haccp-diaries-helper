from __future__ import annotations

from operator import add
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


EntryType = Literal[
    "temperature_fridge",
    "temperature_thermal",
    "incoming_goods",
    "cleaning",
    "personal_hygiene",
    "waste",
    "pest_control",
    "equipment_control",
    "water_control",
    "ddd",
    "traceability",
    "complaints",
    "unknown",
]

InputKind = Literal["text", "voice", "photo", "document", "unknown"]


class InvoiceItem(BaseModel):
    product: str
    quantity: float | int | str = 1
    unit: str = "бр"
    temperature: str = "неизвестна"
    expiry_date: str = "неизвестна"
    package_condition: str = "неизвестна"
    decision: str = "прието"


class ExtractedEntry(BaseModel):
    """Structured diary entry extracted from user input."""

    entry_type: EntryType
    date: str | None = None
    time: str | None = None
    signature: str | None = None

    # temperature_fridge
    fridge_number: str | None = None
    temperature: str | float | None = None
    corrective_action: str | None = None

    # temperature_thermal
    product: str | None = None
    batch: str | None = None
    core_temperature: str | float | None = None
    operator: str | None = None

    # incoming_goods
    supplier: str | None = None
    expiry_date: str | None = None
    package_condition: str | None = None
    documents: str | None = None
    decision: str | None = None
    quantity: str | float | None = None
    unit: str | None = None
    note: str | None = None
    items: list[InvoiceItem] | None = None

    # cleaning
    area: str | None = None
    cleaning_type: str | None = None
    chemical: str | None = None
    frequency: str | None = None
    executor: str | None = None

    # personal_hygiene
    employee: str | None = None
    clean_uniform: str | None = None
    washed_hands: str | None = None
    no_jewelry: str | None = None

    # waste
    waste_type: str | None = None
    container: str | None = None
    disposed_where: str | None = None

    # pest_control
    zone: str | None = None
    observation: str | None = None
    action: str | None = None

    # equipment_control
    equipment: str | None = None
    status: str | None = None

    # water_control
    source: str | None = None
    certificate: str | None = None

    # ddd
    treatment_type: str | None = None
    protocol_number: str | None = None

    # traceability
    used_in: str | None = None

    # complaints
    client: str | None = None
    description: str | None = None
    result: str | None = None

    def to_row_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude={"items"}, exclude_none=False)


class MissingField(BaseModel):
    field: str
    label: str


class WrittenEntry(BaseModel):
    entry_id: str
    entry_type: EntryType
    sheet_name: str
    row_number: int
    data: dict[str, Any]
    missing: list[MissingField] = Field(default_factory=list)


class TelegramUser(BaseModel):
    user_id: str
    chat_id: str
    name: str
    signature: str
    allowed: bool


class GraphState(TypedDict, total=False):
    """LangGraph state for one Telegram message processing run."""

    # Input
    telegram_user_id: str
    chat_id: str
    telegram_user_name: str | None
    input_kind: InputKind
    raw_text: str | None
    file_bytes: bytes | None
    file_mime: str | None

    # Auth
    user: TelegramUser | None

    # Processing
    input_text: str | None
    is_invoice_ocr: bool
    extracted: ExtractedEntry | None
    entries_to_write: list[ExtractedEntry]
    written_entries: list[WrittenEntry]
    validation_errors: list[str]

    # Output
    reply_messages: Annotated[list[str], add]
    access_denied: bool
    help_requested: bool
    pending_handled: bool
    finished: bool
    pending_entry: ExtractedEntry | None
