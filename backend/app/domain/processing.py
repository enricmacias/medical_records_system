"""Processing progress surfaced to the UI while a record is being structured."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProcessingProgress(BaseModel):
    """User-visible progress while `status=processing`. Cleared when completed or failed."""

    percent: int = Field(ge=0, le=100)
    step: str = Field(description="Machine step id, e.g. demographics, clinical_summary.")
    message: str = Field(description="Short user-facing description of the current step.")
