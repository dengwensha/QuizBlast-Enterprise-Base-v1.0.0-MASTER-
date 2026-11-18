"""Atomic copy of a published set into a user-owned quiz.

Caller owns the SQLAlchemy transaction; no commit takes place here.
"""
from fastapi import HTTPException


def clone_question(source, quiz_id, Question):
    return Question(
        quiz_id=quiz_id,
        question=source.question,
        image_url=source.image_url,
        image_alt_text=getattr(source, "image_alt_text", None),
        explanation=source.explanation,
        option1=source.option1,
        option2=source.option2,
        option3=source.option3,
        option4=source.option4,
        correct=source.correct,
        time=source.time,
    )


def copy_published_set(db, set_id, owner_email, Quiz, Question, PublishedQuizSet):
    row = db.query(PublishedQuizSet, Quiz).join(
        Quiz, Quiz.id == PublishedQuizSet.quiz_id
    ).filter(
        PublishedQuizSet.id == set_id,
        PublishedQuizSet.is_published.is_(True),
        Quiz.owner_email.is_(None),
    ).with_for_update(of=PublishedQuizSet).first()
    if row is None:
        raise HTTPException(status_code=404, detail="content_set_not_found")

    record, source_quiz = row
    source_questions = db.query(Question).filter(
        Question.quiz_id == source_quiz.id
    ).order_by(Question.id).all()
    if not source_questions:
        raise HTTPException(status_code=409, detail="content_set_has_no_questions")

    owned_quiz = Quiz(title=source_quiz.title, owner_email=owner_email)
    db.add(owned_quiz)
    db.flush()
    for question in source_questions:
        db.add(clone_question(question, owned_quiz.id, Question))
    db.flush()
    return {
        "id": owned_quiz.id,
        "title": owned_quiz.title,
        "question_count": len(source_questions),
    }
