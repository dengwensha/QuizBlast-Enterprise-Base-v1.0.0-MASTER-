from app.services.qbds_mapper import map_excel_row_to_qbds, qbds_to_legacy_payload
from app.services.validation_service import validate_qbds_question
from app.utils.import_report import ImportReport


row = {
    "QuizName": "II. Dünya Savaşı",
    "Category": "Tarih",
    "Language": "tr",
    "Audience": "Yetişkin",
    "Question": "II. Dünya Savaşı hangi yıl başladı?",
    "OptionA": "1914",
    "OptionB": "1939",
    "OptionC": "1945",
    "OptionD": "1950",
    "Correct": "B",
    "Time": "20",
    "Difficulty": "Orta",
    "QuestionType": "Çoktan Seçmeli",
    "Tags": "tarih,savaş,ww2",
    "Explanation": "Savaş 1939 yılında başladı."
}

dto = map_excel_row_to_qbds(row, row_no=2)
report = ImportReport(total_rows=1)
ok = validate_qbds_question(dto, 2, report)

assert ok is True
assert dto.correct == "B"
assert dto.explanation == "Savaş 1939 yılında başladı."

legacy = qbds_to_legacy_payload(dto)

assert legacy["correct"] == 1
assert legacy["options"][1] == "1939"
assert legacy["explanation"] == "Savaş 1939 yılında başladı."

print("QBDS Mapper manual test passed.")
