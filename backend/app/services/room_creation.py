"""Stage an authorized room in the caller's transaction; never commit here."""
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError


class RoomBuilder:
    def __init__(self, Quiz, Question, PublishedQuizSet, GameRoom, RoomIdentity, generate_pin, pin_in_use):
        self.Quiz, self.Question, self.Published = Quiz, Question, PublishedQuizSet
        self.Room, self.Identity = GameRoom, RoomIdentity
        self.generate_pin, self.pin_in_use = generate_pin, pin_in_use

    def eligible(self, db, email):
        published = db.query(self.Published.id).filter(
            self.Published.quiz_id == self.Quiz.id, self.Published.is_published.is_(True)
        ).exists()
        return db.query(self.Quiz).filter(or_(
            self.Quiz.owner_email == email,
            and_(self.Quiz.owner_email.is_(None), published),
        ))

    def lock_quiz(self, db, quiz_id, email, require_questions=False):
        quiz = self.eligible(db, email).filter(self.Quiz.id == quiz_id).with_for_update().first()
        if quiz is None:
            raise HTTPException(404, detail='quiz_not_found')
        if require_questions and not db.query(self.Question.id).filter_by(quiz_id=quiz_id).first():
            raise HTTPException(409, detail='no_questions')
        return quiz

    def stage(self, db, quiz_id, email):
        for _ in range(20):
            pin = self.generate_pin()
            if self.pin_in_use(pin) or db.get(self.Room, pin) is not None:
                continue
            room = self.Room(pin=pin, quiz_id=quiz_id, host_email=email, phase='lobby',
                             question_index=0, answer_stats=[0, 0, 0, 0],
                             identity=self.Identity(instance_id=uuid4().hex))
            try:
                with db.begin_nested():
                    db.add(room)
                    db.flush()
                return room
            except IntegrityError:
                # A different quiz can allocate the same PIN concurrently.
                continue
        raise HTTPException(503, detail='room_pin_unavailable')
