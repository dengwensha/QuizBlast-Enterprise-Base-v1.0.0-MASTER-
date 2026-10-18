"""Read-only serializers for centrally published quiz sets.

The public preview deliberately excludes correct answers and explanations.
"""
from app.services.content_taxonomy import classify_catalog_set


def serialize_set(set_record, quiz, questions):
    classification = classify_catalog_set(
        getattr(set_record, "collection", None),
        stage=getattr(set_record, "stage", None),
        grade=getattr(set_record, "grade", None),
        subject=getattr(set_record, "subject", None),
        topic=getattr(set_record, "school_topic", None),
    )
    return {
        "id": set_record.id,
        "play_quiz_id": quiz.id,
        "slug": set_record.slug,
        "title": quiz.title,
        "description": set_record.description or "",
        "topic": set_record.topic,
        "audience": set_record.audience,
        "difficulty": set_record.difficulty,
        "version": set_record.version,
        "collection": classification.collection,
        "stage": classification.stage,
        "grade": classification.grade,
        "subject": classification.subject,
        "school_topic": classification.topic,
        "question_count": len(questions),
        "estimated_duration_seconds": sum(q.time for q in questions),
    }


def serialize_preview_question(question):
    return {
        "question": question.question,
        "image_url": question.image_url,
        "options": [
            question.option1, question.option2,
            question.option3, question.option4,
        ],
        "time": question.time,
    }
