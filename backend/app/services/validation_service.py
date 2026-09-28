from app.schemas.qbds import QBDSQuestionDTO
from app.services.validation_engine import validate_question, validate_questions
from app.services.validation_result import ValidationReport


def validate_qbds_question(dto: QBDSQuestionDTO, row_no: int, report: ValidationReport) -> bool:
    return validate_question(dto, row_no, report)
