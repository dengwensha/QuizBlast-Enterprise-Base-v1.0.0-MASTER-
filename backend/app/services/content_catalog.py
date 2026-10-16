"""Read-only serializers for centrally published quiz sets.

The public preview deliberately excludes correct answers and explanations.
"""
def serialize_set(set_record, quiz, questions):
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
