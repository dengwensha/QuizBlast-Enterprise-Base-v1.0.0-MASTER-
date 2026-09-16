import React, { useEffect, useMemo, useState } from "react";
import * as XLSX from "xlsx";
import { QRCodeCanvas } from "qrcode.react";
import confetti from "canvas-confetti";

import QuestionList from "./components/question/QuestionList";
import LeaderboardBoard from "./components/game/LeaderboardBoard";
import ResultReveal from "./components/game/ResultReveal";
import GameOver from "./components/game/GameOver";
import DisplayConnect from "./components/game/DisplayConnect";
import JoinScreen from "./components/game/JoinScreen";
import HostSetup from "./components/game/HostSetup";
import QuestionGame from "./components/game/QuestionGame";

import { APP_URL } from "./services/api";

import { useQuizState } from "./hooks/useQuizState";
import { useGameSession } from "./hooks/useGameSession";

import {
  createRoomRequest,
  startGameRequest,
  nextQuestionRequest,
} from "./services/gameService";

import { useAuth } from "./hooks/useAuth";

import {
  previewImportRequest,
  commitImportRequest,
} from "./services/importService";

const isMobile = window.innerWidth < 700;

export default function App() {
  const {
    user,
    authMode,
    setAuthMode,
    authEmail,
    setAuthEmail,
    authPassword,
    setAuthPassword,
    register,
    login,
    clearAuth,
  } = useAuth();
  const playTone=(f=600,d=120,t='sine')=>{try{const A=window.AudioContext||window.webkitAudioContext; const c=new A(); const o=c.createOscillator(); const g=c.createGain(); o.type=t; o.frequency.value=f; o.connect(g); g.connect(c.destination); g.gain.setValueAtTime(.08,c.currentTime); g.gain.exponentialRampToValueAtTime(.001,c.currentTime+d/1000); o.start(); o.stop(c.currentTime+d/1000);}catch(e){}};
  const fireSmallConfetti=()=>confetti({particleCount:60,spread:70,origin:{y:.7}}); const fireBigConfetti=()=>{const end=Date.now()+3000; const i=setInterval(()=>{if(Date.now()>end){clearInterval(i);return;} confetti({particleCount:40,spread:120,startVelocity:40,origin:{x:Math.random(),y:Math.random()*.5}})},250)};
  const [mode,setMode]=useState(null);
  const {
    roomPin,
    setRoomPin,
    name,
    setName,
    playerName,
    joined,
    players,
    question,
    questionImage,
    options,
    leaderboard,
    currentQuestionIndex,
    questionResult,
    timeLeft,
    answered,
    gameOver,
    answerCount,
    totalPlayers,
    connectWebsocket,
    sendAnswer,
    closeSession,
  } = useGameSession({
    onQuestion: () => playTone(720,140,'triangle'),
    onQuestionResult: () => {
      fireSmallConfetti();
      playTone(950,220,'sine');
    },
    onGameOver: () => {
      fireBigConfetti();
      playTone(600,120,'triangle');
      setTimeout(()=>playTone(760,120,'triangle'),150);
      setTimeout(()=>playTone(920,220,'triangle'),300);
    },
    onCountdown: () => playTone(520,80,'square'),
  });
  const {
    quizzes,
    selectedQuizId,
    setSelectedQuizId,
    selectedQuestions,
    loadQuizzes,
    loadSelectedQuestions,
    createQuizRequestState,
    deleteQuizRequestState,
    addQuestionRequestState,
    deleteQuestionRequestState,
    updateQuestionRequestState,
    clearQuizState,
  } = useQuizState(user);
  const [newQuizTitle,setNewQuizTitle]=useState(''); const [newQuestion,setNewQuestion]=useState(''); const [newImageUrl,setNewImageUrl]=useState(''); const [newOptions,setNewOptions]=useState(['','','','']); const [newCorrect,setNewCorrect]=useState(0); const [newTime,setNewTime]=useState(15);
  const [finalLimit,setFinalLimit]=useState(3); const [aiPrompt,setAiPrompt]=useState(''); const [aiAudience,setAiAudience]=useState('Serbest'); const [aiCount,setAiCount]=useState(5); const [aiDifficulty,setAiDifficulty]=useState('Orta'); const [aiQuestionType,setAiQuestionType]=useState('Ã‡oktan SeÃ§meli'); const [aiInstruction,setAiInstruction]=useState(''); const [aiPreviewQuestions,setAiPreviewQuestions]=useState([]); const [importPreview,setImportPreview]=useState(null); const [importing,setImporting]=useState(false); const [importSummary,setImportSummary]=useState(null);
  const optionColors=['#e21b3c','#1368ce','#d89e00','#26890c'];
  const visiblePlayers=players.filter(p=>p!=='HOST'&&p!=='DISPLAY'); const visibleLeaderboard=leaderboard.filter(p=>p[0]!=='HOST'&&p[0]!=='DISPLAY'); const podium=useMemo(()=>visibleLeaderboard.slice(0,3),[visibleLeaderboard]);
  const logout=()=>{closeSession(); clearAuth(); setMode(null); clearQuizState();};
  const leaveGame=()=>{closeSession(); setMode(null);};
  useEffect(() => {
    if ((mode === "admin" || mode === "host") && selectedQuizId) {
      loadSelectedQuestions(selectedQuizId);
    }
  }, [mode, selectedQuizId]);

  const createQuiz = async () => {
    if (!newQuizTitle.trim()) {
      return alert("Quiz adÄ± gir.");
    }

    const d = await createQuizRequestState(newQuizTitle);

    if (d.error) {
      return alert(d.error);
    }

    setNewQuizTitle("");
  };

  const deleteQuiz = async () => {
    if (!selectedQuizId) {
      return alert("Quiz seÃ§.");
    }

    if (!confirm("Bu quiz ve tÃ¼m sorular silinsin mi?")) {
      return;
    }

    await deleteQuizRequestState();
  };
const addQuestion = async (
  q = newQuestion,
  img = newImageUrl,
  opts = newOptions,
  c = Number(newCorrect),
  tm = Number(newTime)
) => {
  if (!selectedQuizId) return alert("Quiz seÃ§");
  if (!q.trim()) return alert("Soru gir.");
  if (opts.some((o) => !String(o).trim()))
    return alert("4 seÃ§eneÄŸi de doldur.");

  const d = await addQuestionRequestState({
    question: q,
    image_url: img,
    options: opts,
    correct: c,
    time: tm,
  });

  if (d.error) return alert(d.error);

  setNewQuestion("");
  setNewImageUrl("");
  setNewOptions(["", "", "", ""]);
  setNewCorrect(0);
  setNewTime(15);
};  const generateMockAiQuestions=()=>{if(!String(aiPrompt||'').trim())return alert('Konu / Prompt alanÄ± boÅŸ olamaz.');const multipleChoiceTemplates=[{question:'What is the most important point about this topic?',options:['Basic rule','Wrong approach','Unrelated detail','No rule'],correct:0},{question:'Which option is the best practice?',options:['Ignore instructions','Follow the correct procedure','Guess quickly','Skip preparation'],correct:1},{question:'What should participants remember?',options:['The key rule','A random number','An unrelated name','Nothing'],correct:0},{question:'Which statement is correct?',options:['Preparation is important','Rules are unnecessary','Mistakes never happen','Training has no value'],correct:0},{question:'What is the best response in a risky situation?',options:['Stop and check','Continue without thinking','Ignore warnings','Hide the problem'],correct:0}];const trueFalseTemplates=[{question:'Following instructions is important for this topic.',options:['True','False','True and False','Not sure'],correct:0},{question:'Preparation is unnecessary for this topic.',options:['True','False','True and False','Not sure'],correct:1},{question:'Participants should understand the basic rules.',options:['True','False','True and False','Not sure'],correct:0}];const count=Math.min(Math.max(Number(aiCount)||1,1),20);const generated=[];for(let i=0;i<count;i++){let pool=multipleChoiceTemplates;if(aiQuestionType==='DoÄŸru / YanlÄ±ÅŸ')pool=trueFalseTemplates;if(aiQuestionType==='KarÄ±ÅŸÄ±k')pool=i%2===0?multipleChoiceTemplates:trueFalseTemplates;const b=pool[i%pool.length];generated.push({question:b.question,image_url:'',options:b.options,correct:b.correct,time:Number(newTime||15)});}setAiPreviewQuestions(generated);alert(`${count} adet soru Ã¶nizlemeye hazÄ±rlandÄ±. HenÃ¼z quizâ€™e eklenmedi.`);};
  const addAiPreviewToQuiz=async()=>{if(!selectedQuizId)return alert('Ã–nce quiz seÃ§.');if(aiPreviewQuestions.length===0)return alert('Ã–nce AI sorularÄ± oluÅŸtur.');for(const q of aiPreviewQuestions){await addQuestion(q.question,q.image_url,q.options,q.correct,q.time);}await loadQuizzes();await loadSelectedQuestions(selectedQuizId);setAiPreviewQuestions([]);alert('AI sorularÄ± quizâ€™e eklendi.');};
  const removeAiPreviewQuestion=(index)=>setAiPreviewQuestions(aiPreviewQuestions.filter((_,i)=>i!==index));
  const editAiPreviewQuestion=(index)=>{const q=aiPreviewQuestions[index];if(!q)return;const qt=prompt('Soru metni:',q.question);if(qt===null)return;const opts=[...q.options];for(let i=0;i<4;i++){const v=prompt(`SeÃ§enek ${i+1}:`,opts[i]);if(v===null)return;opts[i]=v;}const corr=Number(prompt('DoÄŸru cevap indexi: A=0, B=1, C=2, D=3',q.correct));const tm=Number(prompt('SÃ¼re:',q.time));const u=[...aiPreviewQuestions];u[index]={...q,question:qt,options:opts,correct:Number.isNaN(corr)?q.correct:Math.min(Math.max(corr,0),3),time:Number.isNaN(tm)?q.time:tm};setAiPreviewQuestions(u);};
  const regenerateAiPreviewQuestion=(index)=>{if(!String(aiPrompt||'').trim())return alert('Konu / Prompt alanÄ± boÅŸ olamaz.');const templates=[{question:'Which answer best matches this topic?',options:['The correct principle','Unrelated answer','Random guess','No answer'],correct:0},{question:'What is a useful reminder?',options:['Check the key point','Ignore the topic','Avoid learning','Skip all steps'],correct:0},{question:'Which behavior is recommended?',options:['Careful action','Careless action','No preparation','Ignoring feedback'],correct:0},{question:'True or False: Understanding the topic improves participation.',options:['True','False','True and False','Not sure'],correct:0}];const r=templates[Math.floor(Math.random()*templates.length)];const u=[...aiPreviewQuestions];u[index]={question:r.question,image_url:'',options:r.options,correct:r.correct,time:Number(newTime||15)};setAiPreviewQuestions(u);};
const deleteQuestion = async (id) => {
  if (!confirm("Bu soru silinsin mi?")) return;

  await deleteQuestionRequestState(id);
};  
const editQuestion = async (q) => {
  const question = prompt("Soru metni:", q.question);
  if (question === null) return;

  const options = [...(q.options || ["", "", "", ""])];

  for (let i = 0; i < 4; i++) {
    const value = prompt(`SeÃ§enek ${i + 1}:`, options[i] || "");
    if (value === null) return;
    options[i] = value;
  }

  const correct = Number(
    prompt("DoÄŸru cevap indexi: A=0, B=1, C=2, D=3", q.correct)
  );

  const time = Number(prompt("SÃ¼re:", q.time || 15));
  const image_url = prompt("GÃ¶rsel URL opsiyonel:", q.image_url || "");

  const payload = {
    question,
    image_url: image_url || "",
    options,
    correct: Number.isNaN(correct)
      ? q.correct
      : Math.min(Math.max(correct, 0), 3),
    time: Number.isNaN(time) ? q.time || 15 : time,
  };

  const d = await updateQuestionRequestState(q.id, payload);

  if (d.error) return alert(d.error);
};  const importExcel=async(e)=>{if(!selectedQuizId)return alert('Quiz seÃ§'); const file=e.target.files[0]; if(!file)return; try{setImportSummary(null);setImportPreview(null);const d=await previewImportRequest(user,selectedQuizId,file); if(d.error){alert(d.message||d.error); e.target.value=''; return;} setImportPreview(d); const summary=d.preview_payload?.summary||{}; const issues=d.preview_payload?.issues||[]; const mappingErrors=d.mapping_errors||[]; let message='Excel Ã¶n izleme tamamlandÄ±.\n\n'; message+=`Dosya: ${d.filename||file.name}\n`; message+=`Session: ${d.session_id||'-'}\n`; message+=`Toplam satÄ±r: ${summary.total_rows??0}\n`; message+=`Ã–nizleme satÄ±rÄ±: ${summary.preview_rows??0}\n`; message+=`Import edilebilir: ${summary.importable_rows??0}\n`; message+=`Bloklanan: ${summary.blocked_rows??0}\n`; message+=`Hata: ${summary.error_count??0}\n`; message+=`UyarÄ±: ${summary.warning_count??0}\n`; if(mappingErrors.length>0){message+='\nMapping hatalarÄ±:\n'; mappingErrors.slice(0,8).forEach(err=>{message+=`SatÄ±r ${err.row_no}: ${err.message}\n`;}); if(mappingErrors.length>8)message+=`... ${mappingErrors.length-8} hata daha\n`;} if(issues.length>0){message+='\nValidation detaylarÄ±:\n'; issues.slice(0,10).forEach(issue=>{message+=`SatÄ±r ${issue.row_no} | ${issue.severity} | ${issue.code}: ${issue.message}\n`;}); if(issues.length>10)message+=`... ${issues.length-10} detay daha\n`;} message+='\nUygunsa ekrandaki Import Et butonu ile veritabanÄ±na aktarabilirsin.'; alert(message); console.log('QBDS Preview Result',d); e.target.value='';}catch(err){console.error(err); alert('Excel Ã¶n izleme sÄ±rasÄ±nda hata oluÅŸtu. Backend preview endpoint Ã§alÄ±ÅŸÄ±yor mu kontrol et.'); e.target.value='';}};
  const commitImport=async()=>{if(!selectedQuizId)return alert('Quiz seÃ§');if(!importPreview)return alert('Ã–nce Excel Ã¶n izleme yap.');const items=importPreview.importable_payloads||[];if(items.length===0)return alert('Import edilebilir soru yok.');if(!confirm(`${items.length} soru veritabanÄ±na aktarÄ±lsÄ±n mÄ±?`))return;try{setImporting(true);const d=await commitImportRequest(user,selectedQuizId,{session_id:importPreview.session_id,filename:importPreview.filename,duplicate_policy:'skip',overwrite:false,items});setImportSummary(d);if(d.error){alert(d.message||d.error);return;}alert(`Import tamamlandÄ±.\nAktarÄ±lan: ${d.imported}\nAtlanan: ${d.skipped}\nSession: ${d.session_id}`);setImportPreview(null);await loadQuizzes();await loadSelectedQuestions(selectedQuizId);}catch(err){console.error(err);alert('Import commit sÄ±rasÄ±nda hata oluÅŸtu.');}finally{setImporting(false);}};
  const createRoom = async () => {
  if (!selectedQuizId) return alert("Quiz seÃ§");

  const d = await createRoomRequest(selectedQuizId);

  if (d.error) return alert(d.error);

  setRoomPin(d.room_pin);
  connectWebsocket(d.room_pin, "HOST");
};
  const joinRoom=()=>{if(!roomPin.trim())return alert('PIN gir'); if(!name.trim())return alert('Ä°sim gir'); connectWebsocket(roomPin,name);}; const connectDisplay=()=>{if(!roomPin.trim())return alert('PIN gir'); connectWebsocket(roomPin,'DISPLAY');};
  const startGame=async()=>{playTone(700,100,'triangle'); await startGameRequest(roomPin);};
  const nextQuestion = async () => {
  await nextQuestionRequest(roomPin);
};

  if(!user) return <div style={styles.splash}><div style={styles.joinCard}><h1>QuizBlast ğŸš€</h1><h2>{authMode==='login'?'GiriÅŸ Yap':'KayÄ±t Ol'}</h2><input placeholder="E-posta" value={authEmail} onChange={e=>setAuthEmail(e.target.value)} style={styles.input}/><input placeholder="Åifre" type="password" value={authPassword} onChange={e=>setAuthPassword(e.target.value)} style={styles.input}/><button onClick={authMode==='login'?login:register} style={styles.joinButton}>{authMode==='login'?'GiriÅŸ Yap':'KayÄ±t Ol'}</button><button onClick={()=>setAuthMode(authMode==='login'?'register':'login')} style={{...styles.joinButton,marginTop:10,background:'#333'}}>{authMode==='login'?'Hesap oluÅŸtur':'GiriÅŸ ekranÄ±na dÃ¶n'}</button></div></div>;
  if(!mode) return <div style={styles.splash}><div style={styles.center}><h1 style={styles.logo}>QuizBlast ğŸš€</h1><p style={styles.subtitle}>Multiplayer Quiz Platform</p><p>{user.email}</p><button onClick={()=>{setMode('host');loadQuizzes();}} style={styles.mainButton}>ğŸ¤ Host Game</button><button onClick={()=>setMode('player')} style={styles.mainButton}>ğŸ® Join Game</button><button onClick={()=>setMode('display')} style={styles.mainButton}>ğŸ“º Display Screen</button><button onClick={()=>{setMode('admin');loadQuizzes();}} style={styles.mainButton}>ğŸ§  Admin Panel</button><button onClick={logout} style={{...styles.mainButton,background:'#e21b3c',color:'white'}}>Ã‡Ä±kÄ±ÅŸ Yap</button></div></div>;
  if(mode==='admin') return <AdminView {...{quizzes,selectedQuizId,setSelectedQuizId,newQuizTitle,setNewQuizTitle,createQuiz,deleteQuiz,newQuestion,setNewQuestion,newImageUrl,setNewImageUrl,newOptions,setNewOptions,newCorrect,setNewCorrect,newTime,setNewTime,addQuestion,selectedQuestions,deleteQuestion,editQuestion,importExcel,commitImport,importPreview,importing,importSummary,aiPrompt,setAiPrompt,aiAudience,setAiAudience,aiCount,setAiCount,aiDifficulty,setAiDifficulty,aiQuestionType,setAiQuestionType,aiInstruction,setAiInstruction,aiPreviewQuestions,setAiPreviewQuestions,generateMockAiQuestions,addAiPreviewToQuiz,removeAiPreviewQuestion,editAiPreviewQuestion,regenerateAiPreviewQuestion,setMode}} />;
  if(mode==='host'&&!joined) return <HostSetup {...{quizzes,selectedQuizId,setSelectedQuizId,loadSelectedQuestions,finalLimit,setFinalLimit,createRoom,selectedQuestions,setMode,styles}} />;
  if(mode==='player'&&!joined) return <JoinScreen {...{roomPin,setRoomPin,name,setName,joinRoom,setMode}}styles={styles} />;
  if(mode==='display'&&!joined) return <DisplayConnect {...{roomPin,setRoomPin,connectDisplay,setMode}} styles={styles}/>;

return (
  <div style={styles.app}>
    <div style={styles.topbar}>
      <h1>{mode === "display" ? "ğŸ“º QuizBlast Display" : "QuizBlast ğŸš€"}</h1>
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
          â–¶ Oyunu BaÅŸlat
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
        Oyundan Ã‡Ä±k
      </button>
    </div>

    <div style={styles.container}>
      {!question && !gameOver && (
        <div style={styles.waiting}>
          <h1>Oyuncular Bekleniyor...</h1>
          {visiblePlayers.map((p, i) => (
            <div key={i} style={styles.player}>
              ğŸ‘¤ {p}
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

function AdminView(p){return <div style={styles.app}><div style={styles.topbar}><h1>Admin Quiz Builder ğŸ§ </h1><button onClick={()=>p.setMode(null)} style={styles.hostButton}>Ana MenÃ¼</button></div><div style={styles.container}><div style={styles.card}><h2>Yeni Quiz OluÅŸtur</h2><input placeholder="Quiz adÄ±" value={p.newQuizTitle} onChange={e=>p.setNewQuizTitle(e.target.value)} style={styles.input}/><button onClick={p.createQuiz} style={styles.purpleButton}>Quiz OluÅŸtur</button></div><div style={styles.card}><h2>Quiz SeÃ§</h2><select value={p.selectedQuizId} onChange={e=>p.setSelectedQuizId(e.target.value)} style={styles.input}><option value="">Quiz seÃ§</option>{p.quizzes.map(q=><option key={q.id} value={String(q.id)}>{q.title} ({q.questions?.length||0} soru)</option>)}</select><button onClick={p.deleteQuiz} style={{...styles.purpleButton,background:'#e21b3c'}}>SeÃ§ili Quizâ€™i Sil</button></div><div style={styles.card}><h2>Soru Ekle</h2><textarea placeholder="Soru metni" value={p.newQuestion} onChange={e=>p.setNewQuestion(e.target.value)} style={{...styles.input,minHeight:90}}/><input placeholder="GÃ¶rsel URL opsiyonel" value={p.newImageUrl} onChange={e=>p.setNewImageUrl(e.target.value)} style={styles.input}/>{p.newOptions.map((opt,i)=><input key={i} placeholder={`SeÃ§enek ${i+1}`} value={opt} onChange={e=>{const c=[...p.newOptions]; c[i]=e.target.value; p.setNewOptions(c)}} style={styles.input}/>) }<select value={p.newCorrect} onChange={e=>p.setNewCorrect(e.target.value)} style={styles.input}><option value={0}>DoÄŸru: 1. seÃ§enek</option><option value={1}>DoÄŸru: 2. seÃ§enek</option><option value={2}>DoÄŸru: 3. seÃ§enek</option><option value={3}>DoÄŸru: 4. seÃ§enek</option></select><input type="number" value={p.newTime} onChange={e=>p.setNewTime(e.target.value)} style={styles.input}/><button onClick={()=>p.addQuestion()} style={styles.purpleButton}>Soruyu Ekle</button></div><div style={styles.card}><h2>ğŸ¤– AI Soru OluÅŸturucu</h2><p>Okul, kurumsal eÄŸitim, fuar, etkinlik veya serbest konu iÃ§in soru taslaÄŸÄ± oluÅŸtur.</p><label><b>Konu / Prompt</b></label><textarea placeholder="Ã–rn: Forklift gÃ¼venliÄŸi, ISO 9001 kalite yÃ¶netimi, KadÄ±kÃ¶y tarihi, 5. sÄ±nÄ±f Ä°ngilizce Animals konusu" value={p.aiPrompt} onChange={e=>p.setAiPrompt(e.target.value)} style={{...styles.input,minHeight:80}}/><small>SorularÄ±n hangi konu hakkÄ±nda Ã¼retileceÄŸini yaz.</small><br/><br/><label><b>Hedef Kitle</b></label><select value={p.aiAudience} onChange={e=>p.setAiAudience(e.target.value)} style={styles.input}><option>Ä°lkokul</option><option>Ortaokul</option><option>Lise</option><option>Ãœniversite</option><option>YetiÅŸkin</option><option>Uzman</option><option>Serbest</option></select><label><b>Soru SayÄ±sÄ±</b></label><input type="number" min="1" max="20" value={p.aiCount} onChange={e=>p.setAiCount(e.target.value)} style={styles.input}/><label><b>Zorluk</b></label><select value={p.aiDifficulty} onChange={e=>p.setAiDifficulty(e.target.value)} style={styles.input}><option>Kolay</option><option>Orta</option><option>Zor</option><option>KarÄ±ÅŸÄ±k</option></select><label><b>Soru Tipi</b></label><select value={p.aiQuestionType} onChange={e=>p.setAiQuestionType(e.target.value)} style={styles.input}><option>Ã‡oktan SeÃ§meli</option><option>DoÄŸru / YanlÄ±ÅŸ</option><option>KarÄ±ÅŸÄ±k</option></select><label><b>Ek Talimat</b> <span style={{fontWeight:'normal'}}>(Opsiyonel)</span></label><textarea placeholder="Ã–rn: Ä°ÅŸ gÃ¼venliÄŸi kurallarÄ±na odaklan. Sorular kÄ±sa ve anlaÅŸÄ±lÄ±r olsun." value={p.aiInstruction} onChange={e=>p.setAiInstruction(e.target.value)} style={{...styles.input,minHeight:70}}/><button onClick={p.generateMockAiQuestions} style={styles.purpleButton}>AI SorularÄ±nÄ± Ã–nizle</button>{p.aiPreviewQuestions.length>0&&<div style={{marginTop:20,padding:15,border:'2px dashed #d89e00',borderRadius:14,background:'#fff8e1'}}><h3>AI Ã–nizleme - HenÃ¼z Quizâ€™e Eklenmedi</h3><div style={{background:'#f5f5f5',padding:15,borderRadius:10,marginBottom:20,lineHeight:1.7}}><b>AI AyarlarÄ±</b><br/><b>Konu:</b> {p.aiPrompt}<br/><b>Hedef Kitle:</b> {p.aiAudience}<br/><b>Zorluk:</b> {p.aiDifficulty}<br/><b>Soru Tipi:</b> {p.aiQuestionType}<br/>{p.aiInstruction&&<><b>Ek Talimat:</b> {p.aiInstruction}<br/></>}</div><p>Bu sorular sadece Ã¶nizlemedir. VeritabanÄ±na eklemek iÃ§in aÅŸaÄŸÄ±daki yeÅŸil butona bas.</p>{p.aiPreviewQuestions.map((q,i)=><div key={i} style={styles.questionDetailCard}><div><h4>{i+1}. {q.question}</h4><ol>{q.options.map((opt,index)=><li key={index} style={{fontWeight:q.correct===index?'bold':'normal',color:q.correct===index?'green':'black'}}>{opt} {q.correct===index?'âœ…':''}</li>)}</ol><p><b>SÃ¼re:</b> {q.time} saniye</p><div style={{display:'flex',gap:8,flexWrap:'wrap',marginTop:8}}><button onClick={()=>p.removeAiPreviewQuestion(i)} style={{background:'#e21b3c',color:'white',border:'none',borderRadius:8,padding:'8px 12px',cursor:'pointer'}}>KaldÄ±r</button><button onClick={()=>p.editAiPreviewQuestion(i)} style={{background:'#1368ce',color:'white',border:'none',borderRadius:8,padding:'8px 12px',cursor:'pointer'}}>âœ DÃ¼zenle</button><button onClick={()=>p.regenerateAiPreviewQuestion(i)} style={{background:'#d89e00',color:'white',border:'none',borderRadius:8,padding:'8px 12px',cursor:'pointer'}}>ğŸ”„ Yeniden Ãœret</button></div></div></div>)}<button onClick={p.addAiPreviewToQuiz} style={{...styles.purpleButton,marginTop:15,background:'#26890c'}}>Ã–nizlenen SorularÄ± Quizâ€™e Ekle</button><button onClick={()=>p.setAiPreviewQuestions([])} style={{...styles.purpleButton,marginTop:15,marginLeft:10,background:'#e21b3c'}}>Ã–nizlemeyi Temizle</button></div>}</div><QuestionList title="SeÃ§ili Quiz SorularÄ±" questions={p.selectedQuestions} onDelete={p.deleteQuestion} onEdit={p.editQuestion} showDelete styles={styles}/><div style={styles.card}><h2>Excel Import Ã–n Ä°zleme & Commit</h2><p>QBDS formatÄ± veya eski format desteklenir. Dosya Ã¶nce Ã¶nizlenir, sonra onayla veritabanÄ±na aktarÄ±lÄ±r.</p><input type="file" accept=".xlsx,.xls" onChange={p.importExcel} style={styles.input}/>{p.importPreview&&<div style={{background:'#f5f5f5',padding:15,borderRadius:10,marginTop:10,lineHeight:1.7}}><b>Preview hazÄ±r</b><br/>Dosya: {p.importPreview.filename}<br/>Session: {p.importPreview.session_id}<br/>Import edilebilir: {p.importPreview.preview_payload?.summary?.importable_rows??0}<br/>Bloklanan: {p.importPreview.preview_payload?.summary?.blocked_rows??0}<br/>Hata: {p.importPreview.preview_payload?.summary?.error_count??0}<br/>UyarÄ±: {p.importPreview.preview_payload?.summary?.warning_count??0}<br/><button onClick={p.commitImport} disabled={p.importing} style={{...styles.purpleButton,marginTop:12,background:'#26890c'}}>{p.importing?'Import ediliyor...':'Import Et'}</button></div>}{p.importSummary&&<div style={{background:p.importSummary.error?'#ffe5e5':'#e8f5e9',padding:15,borderRadius:10,marginTop:10,lineHeight:1.7}}><b>Import Summary</b><br/>Durum: {p.importSummary.error?'FAILED':'SUCCESS'}<br/>Session: {p.importSummary.session_id}<br/>AktarÄ±lan: {p.importSummary.imported??0}<br/>Atlanan: {p.importSummary.skipped??0}<br/>Hata: {p.importSummary.failed??0}</div>}<p>Not: Correct alanÄ± A/B/C/D veya geriye dÃ¶nÃ¼k uyumluluk iÃ§in 0/1/2/3 olabilir.</p></div></div></div>}

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