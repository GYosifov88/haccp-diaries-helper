"""Pydantic wrappers used for LLM structured output."""

from pydantic import BaseModel, Field

from haccp.models.state import ExtractedEntry, InvoiceItem


class ExtractionResult(BaseModel):
    output: ExtractedEntry


class InvoiceExtractionResult(BaseModel):
    output: ExtractedEntry = Field(
        description="Incoming goods entry; use items[] for multi-product invoices"
    )


class ClassificationResult(BaseModel):
    entry_type: str = Field(
        description="One of: temperature_fridge, temperature_thermal, incoming_goods, "
        "cleaning, personal_hygiene, waste, pest_control, equipment_control, "
        "water_control, ddd, traceability, complaints"
    )
    confidence: float = Field(ge=0, le=1, default=0.8)


__all__ = [
    "ExtractionResult",
    "InvoiceExtractionResult",
    "ClassificationResult",
    "ExtractedEntry",
    "InvoiceItem",
]
