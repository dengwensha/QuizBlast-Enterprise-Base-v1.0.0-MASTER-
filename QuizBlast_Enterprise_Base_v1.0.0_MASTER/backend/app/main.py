
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from contextlib import contextmanager
import os, random, asyncio, time, uuid
from app.services.excel_reader import read_excel_rows_from_bytes
from app.services.import_pipeline import run_qbds_import_pipeline, build_pipeline_user_message

DATABASE_URL=os.getenv('DATABASE_URL','postgresql://quizblast:quizblast@postgres:5432/quizblast')
SECRET_KEY=os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError('SECRET_KEY env var not set')
ALGORITHM='HS256'
ACCESS_TOKEN_EXPIRE_MINUTES=60*24
CORS_ORIGINS=[o.strip() for o in os.getenv('CORS_ORIGINS','http://localhost:5173').split(',') if o.strip()]

engine=create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal=sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base=declarative_base()

class Quiz(Base):
    __tablename__='quizzes'
    id=Column(Integer, primary_key=True, index=True)
    title=Column(String, nullable=False)
    owner_email=Column(String, nullable=True)
    questions=relationship('Question', back_populates='quiz', cascade='all, delete')

class Question(Base):
    __tablename__='questions'
    id=Column(Integer, primary_key=True, index=True)
    quiz_id=Column(Integer, ForeignKey('quizzes.id'))
    question=Column(String, nullable=False)
    image_url=Column(String, nullable=True)
    option1=Column(String, nullable=False)
    option2=Column(String, nullable=False)
    option3=Column(String, nullable=False)
    option4=Column(String, nullable=False)
    correct=Column(Integer, nullable=False)
    time=Column(Integer, default=15)
    quiz=relationship('Quiz', back_populates='questions')


class ImportHistory(Base):
    __tablename__='import_history'
    id=Column(Integer, primary_key=True, index=True)
    session_id=Column(String, unique=True, nullable=False, index=True)
    filename=Column(String, nullable=True)
    owner_email=Column(String, nullable=True, index=True)
    quiz_id=Column(Integer, nullable=False, index=True)
    created_at=Column(DateTime, default=datetime.utcnow, nullable=False)
    total_rows=Column(Integer, default=0)
    imported_rows=Column(Integer, default=0)
    skipped_rows=Column(Integer, default=0)
    warning_rows=Column(Integer, default=0)
    error_rows=Column(Integer, default=0)
    status=Column(String, default='PENDING')
    message=Column(String, nullable=True)

class User(Base):
    __tablename__='users'
    id=Column(Integer, primary_key=True, index=True)
    email=Column(String, unique=True, nullable=False)
    password_hash=Column(String, nullable=False)

connected=False
while not connected:
    try:
        Base.metadata.create_all(bind=engine)
        connected=True
        print('PostgreSQL connected.')
    except Exception as e:
        print('Waiting PostgreSQL...', e)
        time.sleep(2)

app=FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_origin_regex=os.getenv('CORS_ORIGIN_REGEX','http://.*:5173'), allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

rooms={}; scores={}; current_question_index={}; answered_players={}; room_quiz_map={}; answer_stats_map={}; waiting_next_question={}; game_tasks={}; question_start_time={}

class QuizCreate(BaseModel): title: str
class QuestionCreate(BaseModel):
    question: str
    options: list[str]
    correct: int
    time: int = 15
    image_url: str | None = None
class UserRegister(BaseModel): email: str; password: str
class UserLogin(BaseModel): email: str; password: str

class ImportCommitItem(BaseModel):
    question: str
    options: list[str]
    correct: int
    time: int = 15
    image_url: str | None = None

class ImportCommitRequest(BaseModel):
    session_id: str | None = None
    filename: str | None = None
    duplicate_policy: str = 'skip'
    overwrite: bool = False
    items: list[ImportCommitItem]

pwd_context=CryptContext(schemes=['bcrypt'], deprecated='auto')

@contextmanager
def db_session():
    db=SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def generate_pin(): return str(random.randint(100000,999999))

def generate_import_session_id():
    return f"QB-IMP-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

def normalize_question_text(value: str) -> str:
    return ' '.join((value or '').strip().casefold().split())
def hash_password(password): return pwd_context.hash(password)
def verify_password(password, password_hash): return pwd_context.verify(password, password_hash)

def create_access_token(data: dict):
    to_encode=data.copy()
    expire=datetime.utcnow()+timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({'exp':expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_email(authorization: str | None):
    if not authorization: return None
    try:
        scheme, token = authorization.split(' ')
        if scheme.lower()!='bearer': return None
        payload=jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get('sub')
    except Exception:
        return None

def serialize_question(q):
    return {'id':q.id,'question':q.question,'image_url':q.image_url,'options':[q.option1,q.option2,q.option3,q.option4],'correct':q.correct,'time':q.time}

def get_room_questions(room_pin):
    quiz_id=room_quiz_map.get(room_pin)
    if not quiz_id: return []
    with db_session() as db:
        qs=db.query(Question).filter(Question.quiz_id==quiz_id).all()
        return [serialize_question(q) for q in qs]

def visible_player_count(room_pin):
    return len([p for p in rooms.get(room_pin,[]) if p['name'] not in {'HOST','DISPLAY'}])

@app.get('/')
def root(): return {'status':'running'}

@app.post('/auth/register')
def register_user(data: UserRegister):
    with db_session() as db:
        existing=db.query(User).filter(User.email==data.email).first()
        if existing: return {'error':'user_already_exists'}
        user=User(email=data.email, password_hash=hash_password(data.password))
        db.add(user); db.commit(); db.refresh(user)
        return {'status':'registered','user_id':user.id,'email':user.email}

@app.post('/auth/login')
def login_user(data: UserLogin):
    with db_session() as db:
        user=db.query(User).filter(User.email==data.email).first()
        if not user or not verify_password(data.password, user.password_hash):
            return {'error':'invalid_credentials'}
        token=create_access_token({'sub':user.email,'user_id':user.id})
        return {'access_token':token,'token_type':'bearer','email':user.email}

@app.get('/quizzes')
def get_quizzes(authorization: str | None = Header(default=None)):
    email=get_current_email(authorization)
    if not email: return []
    with db_session() as db:
        quizzes=db.query(Quiz).filter(Quiz.owner_email==email).all()
        return [{'id':qz.id,'title':qz.title,'questions':[{'id':q.id,'question':q.question} for q in qz.questions]} for qz in quizzes]

@app.post('/quizzes')
def create_quiz(data: QuizCreate, authorization: str | None = Header(default=None)):
    email=get_current_email(authorization)
    if not email: return {'error':'unauthorized'}
    with db_session() as db:
        quiz=Quiz(title=data.title, owner_email=email)
        db.add(quiz); db.commit(); db.refresh(quiz)
        return {'id':quiz.id,'title':quiz.title}

@app.post('/quizzes/{quiz_id}/questions')
def add_question(quiz_id:int, data: QuestionCreate, authorization: str | None = Header(default=None)):
    if len(data.options)!=4: return {'error':'4_options_required'}
    email=get_current_email(authorization)
    if not email: return {'error':'unauthorized'}
    with db_session() as db:
        quiz=db.query(Quiz).filter(Quiz.id==quiz_id, Quiz.owner_email==email).first()
        if not quiz: return {'error':'quiz_not_found'}
        q=Question(quiz_id=quiz_id,question=data.question,image_url=data.image_url,option1=data.options[0],option2=data.options[1],option3=data.options[2],option4=data.options[3],correct=data.correct,time=data.time)
        db.add(q); db.commit()
        return {'status':'question_added'}

@app.get('/quizzes/{quiz_id}/questions')
def get_questions(quiz_id:int, authorization: str | None = Header(default=None)):
    email=get_current_email(authorization)
    if not email: return []
    with db_session() as db:
        quiz=db.query(Quiz).filter(Quiz.id==quiz_id, Quiz.owner_email==email).first()
        if not quiz: return []
        qs=db.query(Question).filter(Question.quiz_id==quiz_id).all()
        return [serialize_question(q) for q in qs]

@app.delete('/quizzes/{quiz_id}')
def delete_quiz(quiz_id:int, authorization: str | None = Header(default=None)):
    email=get_current_email(authorization)
    if not email: return {'error':'unauthorized'}
    with db_session() as db:
        quiz=db.query(Quiz).filter(Quiz.id==quiz_id, Quiz.owner_email==email).first()
        if not quiz: return {'error':'quiz_not_found'}
        db.delete(quiz); db.commit()
        return {'status':'quiz_deleted'}

@app.delete('/questions/{question_id}')
def delete_question(question_id:int, authorization: str | None = Header(default=None)):
    email=get_current_email(authorization)
    if not email: return {'error':'unauthorized'}
    with db_session() as db:
        q=db.query(Question).join(Quiz).filter(Question.id==question_id, Quiz.owner_email==email).first()
        if not q: return {'error':'question_not_found'}
        db.delete(q); db.commit()
        return {'status':'question_deleted'}


@app.put('/questions/{question_id}')
def update_question(question_id:int, data: QuestionCreate, authorization: str | None = Header(default=None)):
    if len(data.options)!=4: return {'error':'4_options_required'}
    email=get_current_email(authorization)
    if not email: return {'error':'unauthorized'}
    with db_session() as db:
        q=db.query(Question).join(Quiz).filter(Question.id==question_id, Quiz.owner_email==email).first()
        if not q: return {'error':'question_not_found'}
        q.question=data.question
        q.image_url=data.image_url
        q.option1=data.options[0]
        q.option2=data.options[1]
        q.option3=data.options[2]
        q.option4=data.options[3]
        q.correct=data.correct
        q.time=data.time
        db.commit()
        return {'status':'question_updated'}

@app.get('/create-room/{quiz_id}')
def create_room(quiz_id:int):
    with db_session() as db:
        quiz=db.query(Quiz).filter(Quiz.id==quiz_id).first()
        if not quiz: return {'error':'quiz_not_found'}
    pin=generate_pin()
    rooms[pin]=[]; scores[pin]={}; current_question_index[pin]=0; answered_players[pin]=set()
    room_quiz_map[pin]=quiz_id; answer_stats_map[pin]=[0,0,0,0]; waiting_next_question[pin]=False; question_start_time[pin]=None
    return {'room_pin':pin,'quiz_id':quiz_id}

@app.get('/start-game/{room_pin}')
async def start_game(room_pin:str):
    if room_pin not in rooms: return {'error':'room_not_found'}
    if visible_player_count(room_pin)==0: return {'error':'no_players'}
    current_question_index[room_pin]=0; answered_players[room_pin]=set(); answer_stats_map[room_pin]=[0,0,0,0]
    waiting_next_question[room_pin]=False; question_start_time[room_pin]=None
    old_task=game_tasks.get(room_pin)
    if old_task and not old_task.done(): old_task.cancel()
    game_tasks[room_pin]=asyncio.create_task(game_loop(room_pin))
    return {'status':'started'}

@app.get('/next-question/{room_pin}')
async def next_question(room_pin:str):
    if room_pin not in rooms: return {'error':'room_not_found'}
    questions=get_room_questions(room_pin)
    current_question_index[room_pin]=current_question_index.get(room_pin,0)+1
    waiting_next_question[room_pin]=False
    if current_question_index[room_pin]>=len(questions):
        await safe_broadcast_json(room_pin, {'type':'game_over'})
        return {'status':'game_over'}
    return {'status':'ok','question_index':current_question_index[room_pin]}


@app.post('/quizzes/{quiz_id}/import/preview')
async def preview_quiz_import(
    quiz_id: int,
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None)
):
    '''
    Sprint 2.3.1 Backend Preview Endpoint.

    Reads uploaded Excel file and runs QBDS Import Pipeline.
    Does NOT write anything to database.
    '''
    email = get_current_email(authorization)

    if not email:
        return {'error': 'unauthorized'}

    with db_session() as db:
        quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.owner_email == email).first()

        if not quiz:
            return {'error': 'quiz_not_found'}

    filename = file.filename or ''

    if not filename.lower().endswith(('.xlsx', '.xlsm')):
        return {
            'error': 'invalid_file_type',
            'message': 'Lütfen .xlsx veya .xlsm dosyası yükleyin.'
        }

    content = await file.read()

    try:
        raw_rows = read_excel_rows_from_bytes(content)
        pipeline_result = run_qbds_import_pipeline(raw_rows, first_data_row_no=2)

        result = pipeline_result.to_dict()
        result['message'] = build_pipeline_user_message(pipeline_result)
        result['filename'] = filename
        result['quiz_id'] = quiz_id
        result['session_id'] = generate_import_session_id()
        result['mode'] = 'preview_only'

        return result

    except Exception as exc:
        return {
            'error': 'preview_failed',
            'message': str(exc),
            'filename': filename,
            'quiz_id': quiz_id
        }



@app.post('/quizzes/{quiz_id}/import/commit')
def commit_quiz_import(
    quiz_id: int,
    data: ImportCommitRequest,
    authorization: str | None = Header(default=None)
):
    """
    Sprint 2.3.2B Enterprise Import Commit Endpoint.

    Commits preview-approved importable rows to database in one transaction.
    Initial implementation receives importable payloads from the frontend preview state.
    """
    email = get_current_email(authorization)

    if not email:
        return {'error': 'unauthorized'}

    session_id = data.session_id or generate_import_session_id()
    started_at = time.time()

    if not data.items:
        return {
            'error': 'empty_import',
            'message': 'Import edilecek soru bulunamadı.',
            'session_id': session_id
        }

    imported = 0
    skipped = 0
    failed = 0

    try:
        with db_session() as db:
            quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.owner_email == email).first()

            if not quiz:
                return {'error': 'quiz_not_found'}

            existing_texts = {
                normalize_question_text(q.question)
                for q in db.query(Question).filter(Question.quiz_id == quiz_id).all()
            }
            batch_texts = set()

            history = ImportHistory(
                session_id=session_id,
                filename=data.filename,
                owner_email=email,
                quiz_id=quiz_id,
                total_rows=len(data.items),
                status='RUNNING'
            )
            db.add(history)

            for item in data.items:
                if len(item.options) != 4:
                    failed += 1
                    raise ValueError('Her soru 4 seçenek içermelidir.')

                normalized = normalize_question_text(item.question)
                is_duplicate = normalized in existing_texts or normalized in batch_texts

                if is_duplicate and data.duplicate_policy == 'skip' and not data.overwrite:
                    skipped += 1
                    continue

                q = Question(
                    quiz_id=quiz_id,
                    question=item.question,
                    image_url=item.image_url,
                    option1=item.options[0],
                    option2=item.options[1],
                    option3=item.options[2],
                    option4=item.options[3],
                    correct=item.correct,
                    time=item.time
                )
                db.add(q)
                imported += 1
                batch_texts.add(normalized)

            history.imported_rows = imported
            history.skipped_rows = skipped
            history.warning_rows = skipped
            history.error_rows = failed
            history.status = 'SUCCESS'
            history.message = 'Import commit tamamlandı.'
            db.commit()

        duration = round(time.time() - started_at, 2)
        return {
            'success': True,
            'session_id': session_id,
            'imported': imported,
            'skipped': skipped,
            'warnings': skipped,
            'failed': failed,
            'duration': f'{duration}s'
        }

    except Exception as exc:
        # Main transaction is rolled back by SQLAlchemy if commit is not reached.
        try:
            with db_session() as db:
                failed_history = ImportHistory(
                    session_id=session_id,
                    filename=data.filename,
                    owner_email=email,
                    quiz_id=quiz_id,
                    total_rows=len(data.items),
                    imported_rows=0,
                    skipped_rows=0,
                    warning_rows=0,
                    error_rows=len(data.items),
                    status='FAILED',
                    message=str(exc)
                )
                db.add(failed_history)
                db.commit()
        except Exception:
            pass

        return {
            'error': 'commit_failed',
            'message': str(exc),
            'session_id': session_id,
            'imported': 0,
            'skipped': 0,
            'failed': len(data.items)
        }

@app.get('/imports/history')
def get_import_history(authorization: str | None = Header(default=None)):
    email = get_current_email(authorization)

    if not email:
        return []

    with db_session() as db:
        rows = db.query(ImportHistory).filter(ImportHistory.owner_email == email).order_by(ImportHistory.created_at.desc()).limit(50).all()

        return [
            {
                'session_id': row.session_id,
                'filename': row.filename,
                'quiz_id': row.quiz_id,
                'created_at': row.created_at.isoformat() if row.created_at else None,
                'total_rows': row.total_rows,
                'imported_rows': row.imported_rows,
                'skipped_rows': row.skipped_rows,
                'warning_rows': row.warning_rows,
                'error_rows': row.error_rows,
                'status': row.status,
                'message': row.message
            }
            for row in rows
        ]

@app.websocket('/ws/{room_pin}/{player_name}')
async def websocket_endpoint(websocket: WebSocket, room_pin:str, player_name:str):
    await websocket.accept()
    clean_name=player_name.strip()
    if not clean_name:
        await websocket.send_json({'type':'join_error','reason':'invalid_name'}); await websocket.close(); return
    if room_pin not in rooms:
        await websocket.send_json({'type':'join_error','reason':'room_not_found'}); await websocket.close(); return
    normalized_name=clean_name.casefold()
    existing={p['name'].strip().casefold() for p in rooms.get(room_pin,[])}
    if normalized_name in existing:
        await websocket.send_json({'type':'join_error','reason':'duplicate_name'}); await websocket.close(); return
    rooms[room_pin].append({'name':clean_name,'socket':websocket})
    if room_pin not in scores: scores[room_pin]={}
    if clean_name not in {'HOST','DISPLAY'} and clean_name not in scores[room_pin]:
        scores[room_pin][clean_name]=0
    await broadcast_players(room_pin)
    try:
        while True:
            data=await websocket.receive_json()
            if data.get('type')=='answer':
                if clean_name in {'HOST','DISPLAY'}: continue
                if clean_name in answered_players[room_pin]: continue
                questions=get_room_questions(room_pin); idx=current_question_index[room_pin]
                if idx>=len(questions): continue
                q=questions[idx]; question_time=int(q['time'] or 15)
                started_at=question_start_time.get(room_pin)
                if not started_at: continue
                elapsed=time.time()-started_at
                if elapsed>question_time: continue
                answered_players[room_pin].add(clean_name)
                selected_answer=int(data.get('answer',-1))
                if room_pin not in answer_stats_map: answer_stats_map[room_pin]=[0,0,0,0]
                if 0 <= selected_answer <= 3: answer_stats_map[room_pin][selected_answer]+=1
                server_time_left=max(0, question_time-elapsed)
                if selected_answer==q['correct']:
                    scores[room_pin][clean_name]+=100+int(server_time_left*10)
                leaderboard=sorted(scores[room_pin].items(), key=lambda x:x[1], reverse=True)
                await safe_broadcast_json(room_pin, {'type':'answer_count','count':len(answered_players[room_pin]),'total':visible_player_count(room_pin)})
                await safe_broadcast_json(room_pin, {'type':'leaderboard','scores':leaderboard})
    except WebSocketDisconnect:
        rooms[room_pin]=[p for p in rooms.get(room_pin,[]) if p['name']!=clean_name]
        await broadcast_players(room_pin)

async def game_loop(room_pin):
    while True:
        questions=get_room_questions(room_pin); idx=current_question_index.get(room_pin,0)
        if idx>=len(questions):
            await safe_broadcast_json(room_pin, {'type':'game_over'}); break
        waiting_next_question[room_pin]=False
        await send_question(room_pin)
        question_time=int(questions[idx]['time'] or 15)
        await asyncio.sleep(question_time)
        q=questions[idx]
        await safe_broadcast_json(room_pin, {'type':'question_result','correct':q['correct'],'stats':answer_stats_map.get(room_pin,[0,0,0,0])})
        leaderboard=sorted(scores.get(room_pin,{}).items(), key=lambda x:x[1], reverse=True)
        await safe_broadcast_json(room_pin, {'type':'leaderboard','scores':leaderboard})
        waiting_next_question[room_pin]=True
        while waiting_next_question.get(room_pin,False):
            await asyncio.sleep(0.25)

async def send_question(room_pin):
    questions=get_room_questions(room_pin); idx=current_question_index.get(room_pin,0)
    if idx>=len(questions): return
    answered_players[room_pin]=set(); answer_stats_map[room_pin]=[0,0,0,0]
    question_start_time[room_pin]=time.time()
    q=questions[idx]
    await safe_broadcast_json(room_pin, {'type':'question','question':q['question'],'image_url':q.get('image_url'),'options':q['options'],'index':idx,'time':q['time']})

async def safe_broadcast_json(room_pin, payload):
    alive=[]
    for player in rooms.get(room_pin,[]):
        try:
            await player['socket'].send_json(payload); alive.append(player)
        except Exception:
            pass
    rooms[room_pin]=alive

async def broadcast_players(room_pin):
    await safe_broadcast_json(room_pin, {'type':'players','players':[p['name'] for p in rooms.get(room_pin,[])]})
