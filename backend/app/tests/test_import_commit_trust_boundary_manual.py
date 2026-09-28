import asyncio
from io import BytesIO
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from openpyxl import Workbook

import app.main as main_app


def build_workbook(rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append([
        "Question",
        "OptionA",
        "OptionB",
        "OptionC",
        "OptionD",
        "Correct",
        "Time",
    ])

    for row in rows:
        worksheet.append(row)

    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def create_upload(content: bytes, filename: str = "questions.xlsx") -> UploadFile:
    return UploadFile(
        filename=filename,
        file=BytesIO(content),
    )


def commit(
    quiz_id: int,
    token: str,
    content: bytes,
    filename: str = "questions.xlsx",
):
    return asyncio.run(
        main_app.commit_quiz_import(
            quiz_id,
            create_upload(content, filename),
            authorization=f"Bearer {token}",
        )
    )


def question_count(quiz_id: int) -> int:
    with main_app.db_session() as db:
        return db.query(main_app.Question).filter(
            main_app.Question.quiz_id == quiz_id,
        ).count()


def expect_http_error(expected_status: int, expected_detail: str, action) -> None:
    try:
        action()
    except HTTPException as exc:
        assert exc.status_code == expected_status
        assert exc.detail == expected_detail
        return

    raise AssertionError(
        f"Expected HTTP {expected_status} with detail {expected_detail!r}."
    )


def main() -> None:
    unique = uuid4().hex
    owner_email = f"sr03-{unique}@example.com"
    quiz_id = None
    collision_session_id = f"QB-IMP-SR03-{unique.upper()}"

    try:
        with main_app.db_session() as db:
            quiz = main_app.Quiz(
                title=f"SR-03 trust boundary {unique}",
                owner_email=owner_email,
            )
            db.add(quiz)
            db.commit()
            db.refresh(quiz)
            quiz_id = quiz.id

        token = main_app.create_access_token({"sub": owner_email})

        mixed_workbook = build_workbook([
            ["Valid question", "A", "B", "C", "D", "A", 15],
            ["", "A", "B", "C", "D", "A", 15],
        ])
        mixed_result = commit(quiz_id, token, mixed_workbook)

        assert mixed_result["success"] is True
        assert mixed_result["imported"] == 1
        assert mixed_result["failed"] == 1
        assert mixed_result["session_id"].startswith("QB-IMP-")
        assert question_count(quiz_id) == 1

        invalid_workbook = build_workbook([
            ["", "A", "B", "C", "D", "A", 15],
            ["Invalid time", "A", "B", "C", "D", "A", 1],
        ])
        expect_http_error(
            422,
            "no_importable_rows",
            lambda: commit(quiz_id, token, invalid_workbook),
        )
        assert question_count(quiz_id) == 1

        expect_http_error(
            415,
            "invalid_import_file_type",
            lambda: commit(
                quiz_id,
                token,
                mixed_workbook,
                filename="questions.json",
            ),
        )
        assert question_count(quiz_id) == 1

        with main_app.db_session() as db:
            db.add(main_app.ImportHistory(
                session_id=collision_session_id,
                filename="collision.xlsx",
                owner_email=owner_email,
                quiz_id=quiz_id,
                status="TEST_COLLISION",
            ))
            db.commit()

        original_generator = main_app.generate_import_session_id
        main_app.generate_import_session_id = lambda: collision_session_id

        try:
            rollback_workbook = build_workbook([
                ["Rollback question", "A", "B", "C", "D", "B", 20],
            ])
            rollback_result = commit(quiz_id, token, rollback_workbook)
        finally:
            main_app.generate_import_session_id = original_generator

        assert rollback_result["error"] == "commit_failed"
        assert rollback_result["imported"] == 0
        assert question_count(quiz_id) == 1

        print(
            "PASS — import commit revalidation, invalid-file rejection, "
            "server-owned session identity, and transaction rollback verified."
        )
    finally:
        if quiz_id is not None:
            with main_app.db_session() as db:
                db.query(main_app.ImportHistory).filter(
                    main_app.ImportHistory.owner_email == owner_email,
                ).delete(synchronize_session=False)
                quiz = db.query(main_app.Quiz).filter(
                    main_app.Quiz.id == quiz_id,
                ).first()
                if quiz:
                    db.delete(quiz)
                db.commit()


if __name__ == "__main__":
    main()
