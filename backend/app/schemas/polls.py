"""Input validation for independent, single-choice poll definitions."""
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PollCreate(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=500)
    options: list[str] = Field(min_length=2, max_length=6)

    @field_validator('question')
    @classmethod
    def meaningful_question(cls, value):
        if not value.strip():
            raise ValueError('poll_question_empty')
        return value.strip()

    @field_validator('options')
    @classmethod
    def clean_options(cls, values):
        normalized = [v.strip() for v in values]
        if any(not value or len(value) > 160 for value in normalized):
            raise ValueError('poll_option_invalid')
        if len({value.casefold() for value in normalized}) != len(normalized):
            raise ValueError('poll_option_duplicate')
        return normalized
