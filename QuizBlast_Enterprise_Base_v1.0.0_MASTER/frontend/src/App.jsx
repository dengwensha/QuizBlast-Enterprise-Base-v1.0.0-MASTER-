import React, { useEffect, useMemo, useState } from "react";import * as XLSX from "xlsx";
import { QRCodeCanvas } from "qrcode.react";
import confetti from "canvas-confetti";
import QuestionList from "./components/question/QuestionList";
import LeaderboardBoard from "./components/game/LeaderboardBoard";
import ResultReveal from "./components/game/ResultReveal";
import GameOver from "./components/game/GameOver";
import DisplayConnect from "./components/game/DisplayConnect";
import JoinScreen from "./components/game/JoinScreen";
import HostSetup from "./components/game/HostSetup";
import {
  API,
  WS,
  APP_URL,
  authHeaders,
  jsonAuthHeaders,
} from "./services/api";
import {
  fetchQuizzes,
  fetchQuizQuestions,
  createQuizRequest,
  deleteQuizRequest,
} from "./services/quizService";
import {
  createRoomRequest,
  startGameRequest,
  nextQuestionRequest,
} from "./services/gameService";

const isMobile = window.innerWidth < 700;

export default function App() {
  const [user,setUser]=useState(()=>{const s=localStorage.getItem('quizblast_user'); return s?JSON.parse(s):null;});
  const [authMode,setAuthMode]=useState('login'); const [authEmail,setAuthEmail]=useState(''); const [authPassword,setAuthPassword]=useState('');
  const [mode,setMode]=useState(null); const [roomPin,setRoomPin]=useState(()=>new URLSearchParams(window.location.search).get('pin')||'');
  const [name,setName]=useState(''); const [playerName,setPlayerName]=useState(''); const [joined,setJoined]=useState(false); const [socket,setSocket]=useState(null);
  const [players,setPlayers]=useState([]); const [question,setQuestion]=useState(null); const [questionImage,setQuestionImage]=useState(''); const [options,setOptions]=useState([]);
  const [leaderboard,setLeaderboard]=useState([]); const [currentQuestionIndex,setCurrentQuestionIndex]=useState(0); const [questionResult,setQuestionResult]=useState(null); const [timeLeft,setTimeLeft]=useState(0); const [answered,setAnswered]=useState(false);
  const [gameOver,setGameOver]=useState(false); const [answerCount,setAnswerCount]=useState(0); const [totalPlayers,setTotalPlayers]=useState(0);
  const [quizzes,setQuizzes]=useState([]); const [selectedQuizId,setSelectedQuizId]=useState(''); const [selectedQuestions,setSelectedQuestions]=useState([]);
  const [newQuizTitle,setNewQuizTitle]=useState(''); const [newQuestion,setNewQuestion]=useState(''); const [newImageUrl,setNewImageUrl]=useState(''); const [newOptions,setNewOptions]=useState(['','','','']); const [newCorrect,setNewCorrect]=useState(0); const [newTime,setNewTime]=useState(15);
  const [finalLimit,setFinalLimit]=useState(3); const [aiPrompt,setAiPrompt]=useState(''); const [aiAudience,setAiAudience]=useState('Serbest'); const [aiCount,setAiCount]=useState(5); const [aiDifficulty,setAiDifficulty]=useState('Orta'); const [aiQuestionType,setAiQuestionType]=useState('Çoktan Seçmeli'); const [aiInstruction,setAiInstruction]=useState(''); const [aiPreviewQuestions,setAiPreviewQuestions]=useState([]); const [importPreview,setImportPreview]=useState(null); const [importing,setImporting]=useState(false); const [importSummary,setImportSummary]=useState(null);
  const optionColors=['#e21b3c','#1368ce','#d89e00','#26890c'];
  const visiblePlayers=players.filter(p=>p!=='HOST'&&p!=='DISPLAY'); const visibleLeaderboard=leaderboard.filter(p=>p[0]!=='HOST'&&p[0]!=='DISPLAY'); const podium=useMemo(()=>visibleLeaderboard.slice(0,3),[visibleLeaderboard]);
  const playTone=(f=600,d=120,t='sine')=>{try{const A=window.AudioContext||window.webkitAudioContext; const c=new A(); const o=c.createOscillator(); const g=c.createGain(); o.type=t; o.frequency.value=f; o.connect(g); g.connect(c.destination); g.gain.setValueAtTime(.08,c.currentTime); g.gain.exponentialRampToValueAtTime(.001,c.currentTime+d/1000); o.start(); o.stop(c.currentTime+d/1000);}catch(e){}};
  const fireSmallConfetti=()=>confetti({particleCount:60,spread:70,origin:{y:.7}}); const fireBigConfetti=()=>{const end=Date.now()+3000; const i=setInterval(()=>{if(Date.now()>end){clearInterval(i);return;} confetti({particleCount:40,spread:120,startVelocity:40,origin:{x:Math.random(),y:Math.random()*.5}})},250)};
  const register=async()=>{try{const r=await fetch(`${API}/auth/register`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:authEmail,password:authPassword})}); const d=await r.json(); if(d.error)return alert(d.error); alert('Kayıt başarılı.'); setAuthMode('login');}catch(err){console.error(err); alert('Backend bağlantısı kurulamadı. Mobilde bilgisayar IP adresiyle açtığından ve CORS ayarından emin ol.');}};
  const login=async()=>{try{const r=await fetch(`${API}/auth/login`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:authEmail,password:authPassword})}); const d=await r.json(); if(d.error)return alert('Giriş başarısız'); const u={email:d.email,token:d.access_token}; localStorage.setItem('quizblast_user',JSON.stringify(u)); setUser(u);}catch(err){console.error(err); alert('Backend bağlantısı kurulamadı. Mobilde bilgisayar IP adresiyle açtığından ve CORS ayarından emin ol.');}};
  const resetGame=()=>{setJoined(false); setRoomPin(''); setName(''); setPlayerName(''); setPlayers([]); setQuestion(null); setQuestionImage(''); setOptions([]); setLeaderboard([]); setQuestionResult(null); setTimeLeft(0); setAnswered(false); setGameOver(false); setAnswerCount(0); setTotalPlayers(0); setCurrentQuestionIndex(0);};
  const logout=()=>{if(socket)socket.close(); localStorage.removeItem('quizblast_user'); setUser(null); setMode(null); setSocket(null); resetGame(); setQuizzes([]); setSelectedQuizId(''); setSelectedQuestions([]);};
  const leaveGame=()=>{if(socket)socket.close(); setSocket(null); resetGame(); setMode(null);};
  const loadQuizzes=async()=>{const r=await fetch(`${API}/quizzes`,{headers:authHeaders(user)}); const d=await r.json(); const list=Array.isArray(d)?d:[]; setQuizzes(list); if(list.length>0&&!selectedQuizId)setSelectedQuizId(String(list[0].id));};
  const loadSelectedQuestions=async(id)=>{if(!id){setSelectedQuestions([]);return;} const r=await fetch(`${API}/quizzes/${id}/questions`,{headers:authHeaders(user)}); const d=await r.json(); setSelectedQuestions(Array.isArray(d)?d:[]);};
  useEffect(()=>{if((mode==='admin'||mode==='host')&&selectedQuizId)loadSelectedQuestions(selectedQuizId);},[mode,selectedQuizId]);
  const createQuiz=async()=>{if(!newQuizTitle.trim())return alert('Quiz adı gir.'); const r=await fetch(`${API}/quizzes`,{method:'POST',headers:jsonAuthHeaders(user),body:JSON.stringify({title:newQuizTitle})}); const d=await r.json(); if(d.error)return alert(d.error); setNewQuizTitle(''); setSelectedQuizId(String(d.id)); await loadQuizzes(); await loadSelectedQuestions(String(d.id));};
  const deleteQuiz=async()=>{if(!selectedQuizId)return alert('Quiz seç.'); if(!confirm('Bu quiz ve tüm sorular silinsin mi?'))return; await fetch(`${API}/quizzes/${selectedQuizId}`,{method:'DELETE',headers:authHeaders(user)}); setSelectedQuizId(''); setSelectedQuestions([]); await loadQuizzes();};
  const addQuestion=async(q=newQuestion,img=newImageUrl,opts=newOptions,c=Number(newCorrect),tm=Number(newTime))=>{if(!selectedQuizId)return alert('Quiz seç'); if(!q.trim())return alert('Soru gir.'); if(opts.some(o=>!String(o).trim()))return alert('4 seçeneği de doldur.'); const r=await fetch(`${API}/quizzes/${selectedQuizId}/questions`,{method:'POST',headers:jsonAuthHeaders(user),body:JSON.stringify({question:q,image_url:img,options:opts,correct:c,time:tm})}); const d=await r.json(); if(d.error)return alert(d.error); setNewQuestion(''); setNewImageUrl(''); setNewOptions(['','','','']); setNewCorrect(0); setNewTime(15); await loadQuizzes(); await loadSelectedQuestions(selectedQuizId);};
  const generateMockAiQuestions=()=>{if(!String(aiPrompt||'').trim())return alert('Konu / Prompt alanı boş olamaz.');const multipleChoiceTemplates=[{question:'What is the most important point about this topic?',options:['Basic rule','Wrong approach','Unrelated detail','No rule'],correct:0},{question:'Which option is the best practice?',options:['Ignore instructions','Follow the correct procedure','Guess quickly','Skip preparation'],correct:1},{question:'What should participants remember?',options:['The key rule','A random number','An unrelated name','Nothing'],correct:0},{question:'Which statement is correct?',options:['Preparation is important','Rules are unnecessary','Mistakes never happen','Training has no value'],correct:0},{question:'What is the best response in a risky situation?',options:['Stop and check','Continue without thinking','Ignore warnings','Hide the problem'],correct:0}];const trueFalseTemplates=[{question:'Following instructions is important for this topic.',options:['True','False','True and False','Not sure'],correct:0},{question:'Preparation is unnecessary for this topic.',options:['True','False','True and False','Not sure'],correct:1},{question:'Participants should understand the basic rules.',options:['True','False','True and False','Not sure'],correct:0}];const count=Math.min(Math.max(Number(aiCount)||1,1),20);const generated=[];for(let i=0;i<count;i++){let pool=multipleChoiceTemplates;if(aiQuestionType==='Doğru / Yanlış')pool=trueFalseTemplates;if(aiQuestionType==='Karışık')pool=i%2===0?multipleChoiceTemplates:trueFalseTemplates;const b=pool[i%pool.length];generated.push({question:b.question,image_url:'',options:b.options,correct:b.correct,time:Number(newTime||15)});}setAiPreviewQuestions(generated);alert(`${count} adet soru önizlemeye hazırlandı. Henüz quiz’e eklenmedi.`);};
  const addAiPreviewToQuiz=async()=>{if(!selectedQuizId)return alert('Önce quiz seç.');if(aiPreviewQuestions.length===0)return alert('Önce AI soruları oluştur.');for(const q of aiPreviewQuestions){await addQuestion(q.question,q.image_url,q.options,q.correct,q.time);}await loadQuizzes();await loadSelectedQuestions(selectedQuizId);setAiPreviewQuestions([]);alert('AI soruları quiz’e eklendi.');};
  const removeAiPreviewQuestion=(index)=>setAiPreviewQuestions(aiPreviewQuestions.filter((_,i)=>i!==index));
  const editAiPreviewQuestion=(index)=>{const q=aiPreviewQuestions[index];if(!q)return;const qt=prompt('Soru metni:',q.question);if(qt===null)return;const opts=[...q.options];for(let i=0;i<4;i++){const v=prompt(`Seçenek ${i+1}:`,opts[i]);if(v===null)return;opts[i]=v;}const corr=Number(prompt('Doğru cevap indexi: A=0, B=1, C=2, D=3',q.correct));const tm=Number(prompt('Süre:',q.time));const u=[...aiPreviewQuestions];u[index]={...q,question:qt,options:opts,correct:Number.isNaN(corr)?q.correct:Math.min(Math.max(corr,0),3),time:Number.isNaN(tm)?q.time:tm};setAiPreviewQuestions(u);};
  const regenerateAiPreviewQuestion=(index)=>{if(!String(aiPrompt||'').trim())return alert('Konu / Prompt alanı boş olamaz.');const templates=[{question:'Which answer best matches this topic?',options:['The correct principle','Unrelated answer','Random guess','No answer'],correct:0},{question:'What is a useful reminder?',options:['Check the key point','Ignore the topic','Avoid learning','Skip all steps'],correct:0},{question:'Which behavior is recommended?',options:['Careful action','Careless action','No preparation','Ignoring feedback'],correct:0},{question:'True or False: Understanding the topic improves participation.',options:['True','False','True and False','Not sure'],correct:0}];const r=templates[Math.floor(Math.random()*templates.length)];const u=[...aiPreviewQuestions];u[index]={question:r.question,image_url:'',options:r.options,correct:r.correct,time:Number(newTime||15)};setAiPreviewQuestions(u);};
  const deleteQuestion=async(id)=>{if(!confirm('Bu soru silinsin mi?'))return; await fetch(`${API}/questions/${id}`,{method:'DELETE',headers:authHeaders(user)}); await loadQuizzes(); await loadSelectedQuestions(selectedQuizId);};
  const editQuestion=async(q)=>{const question=prompt('Soru metni:',q.question); if(question===null)return; const options=[...(q.options||['','','',''])]; for(let i=0;i<4;i++){const value=prompt(`Seçenek ${i+1}:`,options[i]||''); if(value===null)return; options[i]=value;} const correct=Number(prompt('Doğru cevap indexi: A=0, B=1, C=2, D=3',q.correct)); const time=Number(prompt('Süre:',q.time||15)); const image_url=prompt('Görsel URL opsiyonel:',q.image_url||''); const payload={question,image_url:image_url||'',options,correct:Number.isNaN(correct)?q.correct:Math.min(Math.max(correct,0),3),time:Number.isNaN(time)?(q.time||15):time}; const r=await fetch(`${API}/questions/${q.id}`,{method:'PUT',headers:jsonAuthHeaders(user),body:JSON.stringify(payload)}); const d=await r.json(); if(d.error)return alert(d.error); await loadQuizzes(); await loadSelectedQuestions(selectedQuizId);};
  const importExcel=async(e)=>{if(!selectedQuizId)return alert('Quiz seç'); const file=e.target.files[0]; if(!file)return; try{setImportSummary(null);setImportPreview(null);const formData=new FormData(); formData.append('file',file); const r=await fetch(`${API}/quizzes/${selectedQuizId}/import/preview`,{method:'POST',headers:authHeaders(user),body:formData}); const d=await r.json(); if(d.error){alert(d.message||d.error); e.target.value=''; return;} setImportPreview(d); const summary=d.preview_payload?.summary||{}; const issues=d.preview_payload?.issues||[]; const mappingErrors=d.mapping_errors||[]; let message='Excel ön izleme tamamlandı.\n\n'; message+=`Dosya: ${d.filename||file.name}\n`; message+=`Session: ${d.session_id||'-'}\n`; message+=`Toplam satır: ${summary.total_rows??0}\n`; message+=`Önizleme satırı: ${summary.preview_rows??0}\n`; message+=`Import edilebilir: ${summary.importable_rows??0}\n`; message+=`Bloklanan: ${summary.blocked_rows??0}\n`; message+=`Hata: ${summary.error_count??0}\n`; message+=`Uyarı: ${summary.warning_count??0}\n`; if(mappingErrors.length>0){message+='\nMapping hataları:\n'; mappingErrors.slice(0,8).forEach(err=>{message+=`Satır ${err.row_no}: ${err.message}\n`;}); if(mappingErrors.length>8)message+=`... ${mappingErrors.length-8} hata daha\n`;} if(issues.length>0){message+='\nValidation detayları:\n'; issues.slice(0,10).forEach(issue=>{message+=`Satır ${issue.row_no} | ${issue.severity} | ${issue.code}: ${issue.message}\n`;}); if(issues.length>10)message+=`... ${issues.length-10} detay daha\n`;} message+='\nUygunsa ekrandaki Import Et butonu ile veritabanına aktarabilirsin.'; alert(message); console.log('QBDS Preview Result',d); e.target.value='';}catch(err){console.error(err); alert('Excel ön izleme sırasında hata oluştu. Backend preview endpoint çalışıyor mu kontrol et.'); e.target.value='';}};
  const commitImport=async()=>{if(!selectedQuizId)return alert('Quiz seç');if(!importPreview)return alert('Önce Excel ön izleme yap.');const items=importPreview.importable_payloads||[];if(items.length===0)return alert('Import edilebilir soru yok.');if(!confirm(`${items.length} soru veritabanına aktarılsın mı?`))return;try{setImporting(true);const r=await fetch(`${API}/quizzes/${selectedQuizId}/import/commit`,{method:'POST',headers:jsonAuthHeaders(user),body:JSON.stringify({session_id:importPreview.session_id,filename:importPreview.filename,duplicate_policy:'skip',overwrite:false,items})});const d=await r.json();setImportSummary(d);if(d.error){alert(d.message||d.error);return;}alert(`Import tamamlandı.\nAktarılan: ${d.imported}\nAtlanan: ${d.skipped}\nSession: ${d.session_id}`);setImportPreview(null);await loadQuizzes();await loadSelectedQuestions(selectedQuizId);}catch(err){console.error(err);alert('Import commit sırasında hata oluştu.');}finally{setImporting(false);}};
  const createRoom = async () => {
  if (!selectedQuizId) return alert("Quiz seç");

  const d = await createRoomRequest(selectedQuizId);

  if (d.error) return alert(d.error);

  setRoomPin(d.room_pin);
  connectWebsocket(d.room_pin, "HOST");
};
  const connectWebsocket=(pin,who)=>{setPlayerName(who); const ws=new WebSocket(`${WS}/ws/${pin}/${encodeURIComponent(who)}`); ws.onopen=()=>{}; ws.onmessage=(event)=>{const d=JSON.parse(event.data); if(d.type==='join_error'){alert(d.reason==='duplicate_name'?'Bu isim zaten odada. Farklı bir isim gir.':d.reason==='room_not_found'?'Oda bulunamadı. PIN kontrol et.':'Geçersiz giriş.'); setJoined(false); setSocket(null); try{ws.close();}catch(e){} return;} if(d.type==='players'){setJoined(true); setPlayers(d.players); setTotalPlayers(d.players.filter(p=>p!=='HOST'&&p!=='DISPLAY').length);} if(d.type==='question'){playTone(720,140,'triangle'); setQuestionResult(null); setQuestion(d.question); setQuestionImage(d.image_url||''); setOptions(d.options); setCurrentQuestionIndex(d.index||0); setTimeLeft(d.time); setAnswered(false); setGameOver(false); setAnswerCount(0);} if(d.type==='answer_count')setAnswerCount(d.count); if(d.type==='question_result'){fireSmallConfetti(); playTone(950,220,'sine'); setQuestionResult(d);} if(d.type==='leaderboard')setLeaderboard(d.scores); if(d.type==='game_over'){fireBigConfetti(); playTone(600,120,'triangle'); setTimeout(()=>playTone(760,120,'triangle'),150); setTimeout(()=>playTone(920,220,'triangle'),300); setQuestion(null); setQuestionImage(''); setOptions([]); setGameOver(true);}}; ws.onclose=()=>{}; ws.onerror=(err)=>{console.error('WebSocket error',err);}; setSocket(ws);};
  const joinRoom=()=>{if(!roomPin.trim())return alert('PIN gir'); if(!name.trim())return alert('İsim gir'); connectWebsocket(roomPin,name);}; const connectDisplay=()=>{if(!roomPin.trim())return alert('PIN gir'); connectWebsocket(roomPin,'DISPLAY');}; 
  const startGame=async()=>{playTone(700,100,'triangle'); await fetch(`${API}/start-game/${roomPin}`);};
  const nextQuestion = async () => {
  await nextQuestionRequest(roomPin);
};
  const sendAnswer=(i)=>{if(!socket||answered||timeLeft<=0)return; socket.send(JSON.stringify({type:'answer',answer:i,timeLeft})); setAnswered(true);};
  useEffect(()=>{if(!joined||timeLeft<=0)return; const timer=setTimeout(()=>setTimeLeft(prev=>{if(prev<=6&&prev>1)playTone(520,80,'square'); return prev-1;}),1000); return()=>clearTimeout(timer);},[joined,timeLeft]);

  if(!user) return <div style={styles.splash}><div style={styles.joinCard}><h1>QuizBlast 🚀</h1><h2>{authMode==='login'?'Giriş Yap':'Kayıt Ol'}</h2><input placeholder="E-posta" value={authEmail} onChange={e=>setAuthEmail(e.target.value)} style={styles.input}/><input placeholder="Şifre" type="password" value={authPassword} onChange={e=>setAuthPassword(e.target.value)} style={styles.input}/><button onClick={authMode==='login'?login:register} style={styles.joinButton}>{authMode==='login'?'Giriş Yap':'Kayıt Ol'}</button><button onClick={()=>setAuthMode(authMode==='login'?'register':'login')} style={{...styles.joinButton,marginTop:10,background:'#333'}}>{authMode==='login'?'Hesap oluştur':'Giriş ekranına dön'}</button></div></div>;
  if(!mode) return <div style={styles.splash}><div style={styles.center}><h1 style={styles.logo}>QuizBlast 🚀</h1><p style={styles.subtitle}>Multiplayer Quiz Platform</p><p>{user.email}</p><button onClick={()=>{setMode('host');loadQuizzes();}} style={styles.mainButton}>🎤 Host Game</button><button onClick={()=>setMode('player')} style={styles.mainButton}>🎮 Join Game</button><button onClick={()=>setMode('display')} style={styles.mainButton}>📺 Display Screen</button><button onClick={()=>{setMode('admin');loadQuizzes();}} style={styles.mainButton}>🧠 Admin Panel</button><button onClick={logout} style={{...styles.mainButton,background:'#e21b3c',color:'white'}}>Çıkış Yap</button></div></div>;
  if(mode==='admin') return <AdminView {...{quizzes,selectedQuizId,setSelectedQuizId,newQuizTitle,setNewQuizTitle,createQuiz,deleteQuiz,newQuestion,setNewQuestion,newImageUrl,setNewImageUrl,newOptions,setNewOptions,newCorrect,setNewCorrect,newTime,setNewTime,addQuestion,selectedQuestions,deleteQuestion,editQuestion,importExcel,commitImport,importPreview,importing,importSummary,aiPrompt,setAiPrompt,aiAudience,setAiAudience,aiCount,setAiCount,aiDifficulty,setAiDifficulty,aiQuestionType,setAiQuestionType,aiInstruction,setAiInstruction,aiPreviewQuestions,setAiPreviewQuestions,generateMockAiQuestions,addAiPreviewToQuiz,removeAiPreviewQuestion,editAiPreviewQuestion,regenerateAiPreviewQuestion,setMode}} />;
  if(mode==='host'&&!joined) return <HostSetup {...{quizzes,selectedQuizId,setSelectedQuizId,loadSelectedQuestions,finalLimit,setFinalLimit,createRoom,selectedQuestions,setMode}} />;
  if(mode==='player'&&!joined) return <JoinScreen {...{roomPin,setRoomPin,name,setName,joinRoom,setMode}}styles={styles} />;
  if(mode==='display'&&!joined) return <DisplayConnect {...{roomPin,setRoomPin,connectDisplay,setMode}} styles={styles}/>;

return (
  <div style={styles.app}>
    <div style={styles.topbar}>
      <h1>{mode === "display" ? "📺 QuizBlast Display" : "QuizBlast 🚀"}</h1>
      <h2>PIN: {roomPin}</h2>

      {roomPin && (mode === "host" || mode === "display") && (
        <div style={styles.qrBox}>
          <QRCodeCanvas
            value={`${APP_URL}?pin=${roomPin}`}
            size={160}
            includeMargin
          />
        </div>
      )}

      {mode === "host" && (
        <button onClick={startGame} style={styles.hostButton}>
          ▶ Oyunu Başlat
        </button>
      )}

      <button
        onClick={leaveGame}
        style={{
          ...styles.hostButton,
          background: "#e21b3c",
          color: "white",
        }}
      >
        Oyundan Çık
      </button>
    </div>

    <div style={styles.container}>
      {!question && !gameOver && (
        <div style={styles.waiting}>
          <h1>Oyuncular Bekleniyor...</h1>
          {visiblePlayers.map((p, i) => (
            <div key={i} style={styles.player}>
              👤 {p}
            </div>
          ))}
        </div>
      )}

      {gameOver && (
        <GameOver
          podium={podium}
          visibleLeaderboard={visibleLeaderboard}
          finalLimit={finalLimit}
          styles={styles}
        />
      )}

      {question && (
        <QuestionGame
          question={question}
          questionImage={questionImage}
          timeLeft={timeLeft}
          answerCount={answerCount}
          totalPlayers={totalPlayers}
          mode={mode}
          playerName={playerName}
          options={options}
          sendAnswer={sendAnswer}
          answered={answered}
          questionResult={questionResult}
          optionColors={optionColors}
          visibleLeaderboard={visibleLeaderboard}
          nextQuestion={nextQuestion}
          currentQuestionIndex={currentQuestionIndex}
          totalQuestions={selectedQuestions.length}
          styles={styles}
        />
      )}
    </div>
  </div>
);
}

function AdminView(p){return <div style={styles.app}><div style={styles.topbar}><h1>Admin Quiz Builder 🧠</h1><button onClick={()=>p.setMode(null)} style={styles.hostButton}>Ana Menü</button></div><div style={styles.container}><div style={styles.card}><h2>Yeni Quiz Oluştur</h2><input placeholder="Quiz adı" value={p.newQuizTitle} onChange={e=>p.setNewQuizTitle(e.target.value)} style={styles.input}/><button onClick={p.createQuiz} style={styles.purpleButton}>Quiz Oluştur</button></div><div style={styles.card}><h2>Quiz Seç</h2><select value={p.selectedQuizId} onChange={e=>p.setSelectedQuizId(e.target.value)} style={styles.input}><option value="">Quiz seç</option>{p.quizzes.map(q=><option key={q.id} value={String(q.id)}>{q.title} ({q.questions?.length||0} soru)</option>)}</select><button onClick={p.deleteQuiz} style={{...styles.purpleButton,background:'#e21b3c'}}>Seçili Quiz’i Sil</button></div><div style={styles.card}><h2>Soru Ekle</h2><textarea placeholder="Soru metni" value={p.newQuestion} onChange={e=>p.setNewQuestion(e.target.value)} style={{...styles.input,minHeight:90}}/><input placeholder="Görsel URL opsiyonel" value={p.newImageUrl} onChange={e=>p.setNewImageUrl(e.target.value)} style={styles.input}/>{p.newOptions.map((opt,i)=><input key={i} placeholder={`Seçenek ${i+1}`} value={opt} onChange={e=>{const c=[...p.newOptions]; c[i]=e.target.value; p.setNewOptions(c)}} style={styles.input}/>) }<select value={p.newCorrect} onChange={e=>p.setNewCorrect(e.target.value)} style={styles.input}><option value={0}>Doğru: 1. seçenek</option><option value={1}>Doğru: 2. seçenek</option><option value={2}>Doğru: 3. seçenek</option><option value={3}>Doğru: 4. seçenek</option></select><input type="number" value={p.newTime} onChange={e=>p.setNewTime(e.target.value)} style={styles.input}/><button onClick={()=>p.addQuestion()} style={styles.purpleButton}>Soruyu Ekle</button></div><div style={styles.card}><h2>🤖 AI Soru Oluşturucu</h2><p>Okul, kurumsal eğitim, fuar, etkinlik veya serbest konu için soru taslağı oluştur.</p><label><b>Konu / Prompt</b></label><textarea placeholder="Örn: Forklift güvenliği, ISO 9001 kalite yönetimi, Kadıköy tarihi, 5. sınıf İngilizce Animals konusu" value={p.aiPrompt} onChange={e=>p.setAiPrompt(e.target.value)} style={{...styles.input,minHeight:80}}/><small>Soruların hangi konu hakkında üretileceğini yaz.</small><br/><br/><label><b>Hedef Kitle</b></label><select value={p.aiAudience} onChange={e=>p.setAiAudience(e.target.value)} style={styles.input}><option>İlkokul</option><option>Ortaokul</option><option>Lise</option><option>Üniversite</option><option>Yetişkin</option><option>Uzman</option><option>Serbest</option></select><label><b>Soru Sayısı</b></label><input type="number" min="1" max="20" value={p.aiCount} onChange={e=>p.setAiCount(e.target.value)} style={styles.input}/><label><b>Zorluk</b></label><select value={p.aiDifficulty} onChange={e=>p.setAiDifficulty(e.target.value)} style={styles.input}><option>Kolay</option><option>Orta</option><option>Zor</option><option>Karışık</option></select><label><b>Soru Tipi</b></label><select value={p.aiQuestionType} onChange={e=>p.setAiQuestionType(e.target.value)} style={styles.input}><option>Çoktan Seçmeli</option><option>Doğru / Yanlış</option><option>Karışık</option></select><label><b>Ek Talimat</b> <span style={{fontWeight:'normal'}}>(Opsiyonel)</span></label><textarea placeholder="Örn: İş güvenliği kurallarına odaklan. Sorular kısa ve anlaşılır olsun." value={p.aiInstruction} onChange={e=>p.setAiInstruction(e.target.value)} style={{...styles.input,minHeight:70}}/><button onClick={p.generateMockAiQuestions} style={styles.purpleButton}>AI Sorularını Önizle</button>{p.aiPreviewQuestions.length>0&&<div style={{marginTop:20,padding:15,border:'2px dashed #d89e00',borderRadius:14,background:'#fff8e1'}}><h3>AI Önizleme - Henüz Quiz’e Eklenmedi</h3><div style={{background:'#f5f5f5',padding:15,borderRadius:10,marginBottom:20,lineHeight:1.7}}><b>AI Ayarları</b><br/><b>Konu:</b> {p.aiPrompt}<br/><b>Hedef Kitle:</b> {p.aiAudience}<br/><b>Zorluk:</b> {p.aiDifficulty}<br/><b>Soru Tipi:</b> {p.aiQuestionType}<br/>{p.aiInstruction&&<><b>Ek Talimat:</b> {p.aiInstruction}<br/></>}</div><p>Bu sorular sadece önizlemedir. Veritabanına eklemek için aşağıdaki yeşil butona bas.</p>{p.aiPreviewQuestions.map((q,i)=><div key={i} style={styles.questionDetailCard}><div><h4>{i+1}. {q.question}</h4><ol>{q.options.map((opt,index)=><li key={index} style={{fontWeight:q.correct===index?'bold':'normal',color:q.correct===index?'green':'black'}}>{opt} {q.correct===index?'✅':''}</li>)}</ol><p><b>Süre:</b> {q.time} saniye</p><div style={{display:'flex',gap:8,flexWrap:'wrap',marginTop:8}}><button onClick={()=>p.removeAiPreviewQuestion(i)} style={{background:'#e21b3c',color:'white',border:'none',borderRadius:8,padding:'8px 12px',cursor:'pointer'}}>Kaldır</button><button onClick={()=>p.editAiPreviewQuestion(i)} style={{background:'#1368ce',color:'white',border:'none',borderRadius:8,padding:'8px 12px',cursor:'pointer'}}>✏ Düzenle</button><button onClick={()=>p.regenerateAiPreviewQuestion(i)} style={{background:'#d89e00',color:'white',border:'none',borderRadius:8,padding:'8px 12px',cursor:'pointer'}}>🔄 Yeniden Üret</button></div></div></div>)}<button onClick={p.addAiPreviewToQuiz} style={{...styles.purpleButton,marginTop:15,background:'#26890c'}}>Önizlenen Soruları Quiz’e Ekle</button><button onClick={()=>p.setAiPreviewQuestions([])} style={{...styles.purpleButton,marginTop:15,marginLeft:10,background:'#e21b3c'}}>Önizlemeyi Temizle</button></div>}</div><QuestionList title="Seçili Quiz Soruları" questions={p.selectedQuestions} onDelete={p.deleteQuestion} onEdit={p.editQuestion} showDelete styles={styles}/><div style={styles.card}><h2>Excel Import Ön İzleme & Commit</h2><p>QBDS formatı veya eski format desteklenir. Dosya önce önizlenir, sonra onayla veritabanına aktarılır.</p><input type="file" accept=".xlsx,.xls" onChange={p.importExcel} style={styles.input}/>{p.importPreview&&<div style={{background:'#f5f5f5',padding:15,borderRadius:10,marginTop:10,lineHeight:1.7}}><b>Preview hazır</b><br/>Dosya: {p.importPreview.filename}<br/>Session: {p.importPreview.session_id}<br/>Import edilebilir: {p.importPreview.preview_payload?.summary?.importable_rows??0}<br/>Bloklanan: {p.importPreview.preview_payload?.summary?.blocked_rows??0}<br/>Hata: {p.importPreview.preview_payload?.summary?.error_count??0}<br/>Uyarı: {p.importPreview.preview_payload?.summary?.warning_count??0}<br/><button onClick={p.commitImport} disabled={p.importing} style={{...styles.purpleButton,marginTop:12,background:'#26890c'}}>{p.importing?'Import ediliyor...':'Import Et'}</button></div>}{p.importSummary&&<div style={{background:p.importSummary.error?'#ffe5e5':'#e8f5e9',padding:15,borderRadius:10,marginTop:10,lineHeight:1.7}}><b>Import Summary</b><br/>Durum: {p.importSummary.error?'FAILED':'SUCCESS'}<br/>Session: {p.importSummary.session_id}<br/>Aktarılan: {p.importSummary.imported??0}<br/>Atlanan: {p.importSummary.skipped??0}<br/>Hata: {p.importSummary.failed??0}</div>}<p>Not: Correct alanı A/B/C/D veya geriye dönük uyumluluk için 0/1/2/3 olabilir.</p></div></div></div>}

const styles={splash:{minHeight:'100vh',background:'linear-gradient(135deg,#46178f,#6c2bd9)',display:'flex',justifyContent:'center',alignItems:'center',color:'white',fontFamily:'Arial',padding:16},center:{textAlign:'center'},logo:{fontSize:isMobile?42:64,marginBottom:10},subtitle:{fontSize:isMobile?18:22,marginBottom:30},mainButton:{display:'block',width:isMobile?'100%':320,padding:18,margin:'15px auto',fontSize:isMobile?18:22,borderRadius:18,border:'none',cursor:'pointer',fontWeight:'bold'},app:{minHeight:'100vh',background:'#f2f2f2',fontFamily:'Arial'},topbar:{background:'#46178f',color:'white',padding:16,textAlign:'center',display:'flex',flexWrap:'wrap',justifyContent:'center',alignItems:'center',gap:12},container:{maxWidth:1200,margin:'0 auto',padding:isMobile?12:20},card:{background:'white',color:'black',padding:isMobile?16:25,borderRadius:18,marginBottom:20,boxShadow:'0 4px 12px rgba(0,0,0,0.12)'},input:{width:'100%',padding:14,marginBottom:12,fontSize:17,boxSizing:'border-box'},purpleButton:{padding:14,background:'#46178f',color:'white',border:'none',borderRadius:12,fontSize:18,cursor:'pointer'},deleteButton:{padding:'8px 12px',background:'#e21b3c',color:'white',border:'none',borderRadius:8,cursor:'pointer'},questionDetailCard:{display:'flex',flexDirection:isMobile?'column':'row',justifyContent:'space-between',alignItems:'flex-start',padding:16,borderBottom:'1px solid #ddd',gap:20},joinCard:{background:'white',color:'black',padding:isMobile?24:40,borderRadius:20,width:isMobile?'100%':350,textAlign:'center'},joinButton:{width:'100%',padding:15,background:'#46178f',color:'white',border:'none',fontSize:18,borderRadius:10},hostButton:{padding:'12px 24px',border:'none',borderRadius:12,background:'white',color:'#46178f',fontWeight:'bold',cursor:'pointer'},qrBox:{background:'white',padding:14,borderRadius:16,margin:10},waiting:{textAlign:'center',marginTop:isMobile?40:80},player:{fontSize:isMobile?22:28,margin:10},questionCard:{background:'white',borderRadius:20,padding:isMobile?18:30,textAlign:'center',marginBottom:20,boxShadow:'0 4px 12px rgba(0,0,0,0.15)'},questionImage:{maxWidth:'100%',maxHeight:isMobile?220:360,objectFit:'contain',borderRadius:18,margin:'20px auto',display:'block',boxShadow:'0 4px 14px rgba(0,0,0,0.18)'},previewImage:{maxWidth:260,maxHeight:160,objectFit:'contain',borderRadius:12,margin:'10px 0',display:'block',border:'1px solid #ddd'},timerCircle:{width:isMobile?90:120,height:isMobile?90:120,borderRadius:'50%',background:'#46178f',color:'white',fontSize:isMobile?36:48,display:'flex',justifyContent:'center',alignItems:'center',margin:'20px auto'},progressOuter:{height:20,background:'#ddd',borderRadius:20,overflow:'hidden'},progressInner:{height:'100%',background:'#46178f',transition:'1s linear'},answers:{display:'grid',gridTemplateColumns:isMobile?'1fr':'1fr 1fr',gap:16},answerButton:{color:'white',border:'none',padding:isMobile?24:40,fontSize:isMobile?20:28,borderRadius:20,minHeight:isMobile?110:180,cursor:'pointer',fontWeight:'bold'},answered:{marginTop:20,textAlign:'center',fontSize:24,color:'green',fontWeight:'bold'},board:{background:'white',borderRadius:20,padding:20,marginTop:30},boardRow:{display:'flex',justifyContent:'space-between',padding:10,fontSize:isMobile?18:22,borderBottom:'1px solid #ddd'},gameOver:{textAlign:'center',marginTop:60},gameOverTitle:{fontSize:isMobile?42:64,color:'#46178f'},podium:{display:'flex',flexDirection:isMobile?'column':'row',justifyContent:'center',alignItems:'center',gap:20,marginTop:40},podiumItem:{width:isMobile?'100%':220,borderRadius:20,color:'black',display:'flex',flexDirection:'column',justifyContent:'center',alignItems:'center',fontWeight:'bold',boxShadow:'0 4px 12px rgba(0,0,0,0.2)'},finalBoard:{background:'white',borderRadius:20,padding:20,marginTop:40},finalRow:{display:'flex',justifyContent:'space-between',padding:15,fontSize:isMobile?18:24,borderBottom:'1px solid #ddd'},
  liveStage: {
    width: "100%",
    maxWidth: 1600,
    margin: "0 auto",
    padding: isMobile ? 10 : 20
  },

  liveQuestionCard: {
    background: "white",
    borderRadius: 28,
    padding: isMobile ? 22 : 38,
    textAlign: "center",
    marginBottom: 24,
    boxShadow: "0 8px 24px rgba(0,0,0,0.18)",
    animation: "stagePop 0.55s ease-out"
  },

  liveQuestionText: {
    fontSize: isMobile ? 38 : 72,
    fontWeight: "900",
    lineHeight: 1.18,
    color: "#111",
    marginBottom: 20
  },

  liveQuestionImage: {
    maxWidth: "100%",
    maxHeight: isMobile ? 220 : 420,
    objectFit: "contain",
    borderRadius: 20,
    margin: "10px auto 24px",
    display: "block",
    boxShadow: "0 5px 18px rgba(0,0,0,0.18)"
  },

  liveTimer: {
    width: isMobile ? 110 : 150,
    height: isMobile ? 110 : 150,
    borderRadius: "50%",
    background: "#46178f",
    color: "white",
    fontSize: isMobile ? 46 : 70,
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    margin: "18px auto",
    fontWeight: "900",
    boxShadow: "0 6px 16px rgba(70,23,143,0.35)"
  },

  liveProgressOuter: {
    height: 24,
    background: "#ddd",
    borderRadius: 24,
    overflow: "hidden",
    marginTop: 12
  },

  liveProgressInner: {
    height: "100%",
    background: "#46178f",
    transition: "1s linear"
  },

  liveAnswerCount: {
    marginTop: 14,
    fontSize: isMobile ? 18 : 24,
    fontWeight: "800"
  },

  liveOptionsGrid: {
    display: "grid",
    gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr",
    gap: isMobile ? 14 : 22,
    marginTop: 22,
    marginBottom: 26
  },

  liveOptionCard: {
    minHeight: isMobile ? 130 : 210,
    borderRadius: 24,
    color: "white",
    display: "flex",
    alignItems: "center",
    gap: 20,
    padding: isMobile ? 18 : 28,
    boxShadow: "0 8px 18px rgba(0,0,0,0.25)",
    animation: "optionEnter 0.7s ease-out both",
    transformOrigin: "center",
    fontWeight: "900"
  },

  liveOptionLetter: {
    width: isMobile ? 48 : 68,
    height: isMobile ? 48 : 68,
    borderRadius: "50%",
    background: "rgba(255,255,255,0.22)",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    fontSize: isMobile ? 24 : 36,
    flexShrink: 0
  },

  liveOptionText: {
    fontSize: isMobile ? 28 : 44,
    lineHeight: 1.15,
    textAlign: "left"
  },

  liveResultCard: {
    background: "white",
    borderRadius: 28,
    padding: isMobile ? 22 : 34,
    marginTop: 24,
    marginBottom: 24,
    boxShadow: "0 8px 24px rgba(0,0,0,0.18)",
    animation: "resultReveal 0.65s ease-out"
  },

  liveResultTitle: {
    fontSize: isMobile ? 30 : 46,
    color: "#46178f",
    textAlign: "center"
  },

  liveCorrectAnswer: {
    color: "white",
    padding: isMobile ? 20 : 30,
    borderRadius: 24,
    fontSize: isMobile ? 28 : 44,
    fontWeight: "900",
    marginBottom: 24,
    textAlign: "center",
    boxShadow: "0 6px 18px rgba(0,0,0,0.22)",
    animation: "correctPulse 0.8s ease-out"
  },

  correctAnswer: {
    color: "white",
    padding: 20,
    borderRadius: 16,
    fontSize: isMobile ? 22 : 28,
    fontWeight: "bold",
    marginBottom: 20,
    textAlign: "center"
  },

  resultRow: {
    marginBottom: 14
  },

  resultLabel: {
    marginBottom: 6,
    fontWeight: "bold"
  },

  liveResultLabel: {
    marginBottom: 8,
    fontWeight: "900",
    fontSize: isMobile ? 17 : 22
  },

  resultBarOuter: {
    width: "100%",
    height: 36,
    background: "#eee",
    borderRadius: 18,
    overflow: "hidden"
  },

  resultBarInner: {
    height: "100%",
    color: "white",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: "900",
    transition: "width 0.8s ease"
  },

  liveBoard: {
    background: "white",
    borderRadius: 24,
    padding: isMobile ? 18 : 26,
    marginTop: 24,
    boxShadow: "0 5px 18px rgba(0,0,0,0.14)",
    animation: "stagePop 0.55s ease-out"
  },

  liveBoardRow: {
    display: "flex",
    justifyContent: "space-between",
    padding: isMobile ? 12 : 16,
    fontSize: isMobile ? 20 : 28,
    borderBottom: "1px solid #ddd",
    fontWeight: "800"
  },

  podiumGold:{animation:'podiumRise .9s ease-out'},podiumSilver:{animation:'podiumRise 1.2s ease-out'},podiumBronze:{animation:'podiumRise 1.5s ease-out'}};
if(typeof document!=='undefined'&&!document.getElementById('quizblast-podium-keyframes')){const s=document.createElement('style'); s.id='quizblast-podium-keyframes'; s.innerText=`@keyframes podiumRise{0%{transform:translateY(80px) scale(.8);opacity:0}60%{transform:translateY(-10px) scale(1.05);opacity:1}100%{transform:translateY(0) scale(1);opacity:1}}`; document.head.appendChild(s);}
