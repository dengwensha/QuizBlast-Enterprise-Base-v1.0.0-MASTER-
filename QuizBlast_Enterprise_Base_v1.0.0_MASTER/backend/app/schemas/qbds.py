from pydantic import BaseModel, Field
from typing import Optional


# DTO intentionally keeps these as strings.
# Validation Engine owns business-rule validation and produces row-level import issues.
CorrectLetter = str
Difficulty = str
QuestionType = str


class QBDSQuestionDTO(BaseModel):
    quiz_name: Optional[str] = None
    category: Optional[str] = None
    language: str = "tr"
    audience: str = "Serbest"

    question: str
    image: Optional[str] = None

    option_a: str
    option_b: str
    option_c: str
    option_d: str

    correct: CorrectLetter
    time: int = 15
    difficulty: Difficulty = "Orta"
    question_type: QuestionType = "Çoktan Seçmeli"

    tags: list[str] = Field(default_factory=list)
    notes: Optional[str] = None

    def to_legacy_question_create(self) -> dict:
        correct_map = {
            "A": 0,
            "B": 1,
            "C": 2,
            "D": 3
        }

        return {
            "question": self.question,
            "image_url": self.image or "",
            "options": [
                self.option_a,
                self.option_b,
                self.option_c,
                self.option_d
            ],
            "correct": correct_map[self.correct],
            "time": self.time
        }
