"""Strict request contracts for private event drafts."""
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventFields(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1, max_length=160)
    organization: str | None = Field(default=None, max_length=160)
    scheduled_at: datetime | None = None

    @field_validator('title', 'organization', mode='before')
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator('scheduled_at')
    @classmethod
    def require_timezone(cls, value):
        if value is not None:
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError('scheduled_at must include a timezone')
            return value.astimezone(timezone.utc)
        return value


class EventCreate(EventFields):
    pass


class EventUpdate(EventFields):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    revision: int = Field(ge=1, strict=True)

    @field_validator('title')
    @classmethod
    def title_cannot_be_null(cls, value):
        if value is None:
            raise ValueError('title cannot be null')
        return value


class EventQuizSelect(BaseModel):
    model_config = ConfigDict(extra='forbid')
    quiz_id: int = Field(gt=0, strict=True)
    revision: int = Field(ge=1, strict=True)


class EventSessionCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: int = Field(ge=1, strict=True)


class AgendaStep(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    kind: Literal['presentation', 'quiz', 'break']
    slide_seconds: int | None = Field(default=None, ge=3, le=300, strict=True)
    deck_id: UUID | None = None
    step_id: UUID | None = None
    quiz_id: int | None = Field(default=None, gt=0, strict=True)
    title: str = Field(min_length=1, max_length=160)


class EventAgendaUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: int = Field(ge=1, strict=True)
    retention: Literal['keep', 'delete_after_7_days'] | None = None
    steps: list[AgendaStep] = Field(max_length=50)


class EventRunCommand(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Literal['open', 'complete', 'previous_page', 'next_page']
    revision: int = Field(ge=1, strict=True)


class SlideCommand(EventSessionCreate):
    action: Literal['previous_page', 'next_page']
