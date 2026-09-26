import React, { useEffect, useMemo, useState } from "react";
import { QRCodeCanvas } from "qrcode.react";
import confetti from "canvas-confetti";

import AdminView from "./components/admin/AdminView.jsx";
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

import { useAdminState } from "./hooks/useAdminState";

import { useImportState } from "./hooks/useImportState";

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
  const [mode,setMode]=useState(() => {
    try {
      const saved=JSON.parse(sessionStorage.getItem('quizblast_active_session'));
      return saved?.who==='HOST'?'host':saved?.who==='DISPLAY'?'display':saved?.who?'player':null;
    } catch { return null; }
  });
  const {
    roomPin,
    setRoomPin,
    name,
    setName,
    playerName,
    joined,
    reconnecting,
    players,
    question,
    questionImage,
    options,
    leaderboard,
    currentQuestionIndex,
    totalQuestions,
    questionResult,
    timeLeft,
    answered,
    gameOver,
    paused,
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
  const {
    importPreview,
    importing,
    importSummary,
    importExcel,
    commitImport,
  } = useImportState({
    user,
    selectedQuizId,
    onImportCommitted: async (quizId) => {
      await loadQuizzes();
      await loadSelectedQuestions(quizId);
    },
  });
  const admin = useAdminState({
    user,
    selectedQuizId,
    createQuizRequestState,
    deleteQuizRequestState,
    addQuestionRequestState,
    deleteQuestionRequestState,
    updateQuestionRequestState,
    loadQuizzes,
    loadSelectedQuestions
  });
  const [finalLimit,setFinalLimit]=useState(3);
  const optionColors=['#e21b3c','#1368ce','#d89e00','#26890c'];
  const visiblePlayers=players.filter(p=>p!=='HOST'&&p!=='DISPLAY'); const visibleLeaderboard=leaderboard.filter(p=>p[0]!=='HOST'&&p[0]!=='DISPLAY'); const podium=useMemo(()=>visibleLeaderboard.slice(0,3),[visibleLeaderboard]);
  const logout=()=>{closeSession(); clearAuth(); setMode(null); clearQuizState();};
  const leaveGame=()=>{closeSession(); setMode(null);};
  useEffect(() => {
    let saved;
    try { saved=JSON.parse(sessionStorage.getItem('quizblast_active_session')); }
    catch { return; }
    if (saved?.pin && saved?.who && user?.token) {
      setRoomPin(saved.pin);
      connectWebsocket(saved.pin,saved.who,saved.who==='HOST'?user.token:undefined);
    }
  }, [user?.token]);
  useEffect(() => {
    if ((mode === "admin" || mode === "host") && selectedQuizId) {
      loadSelectedQuestions(selectedQuizId);
    }
  }, [mode, selectedQuizId]);

  const createRoom = async () => {
  if (!selectedQuizId) return alert("Quiz seç");

  const d = await createRoomRequest(
    selectedQuizId,
    user.token
  );

  if (d.error) return alert(d.error);

  setRoomPin(d.room_pin);
  connectWebsocket(d.room_pin, "HOST", user.token);
};
  const joinRoom=()=>{if(!roomPin.trim())return alert('PIN gir'); if(!name.trim())return alert('İsim gir'); connectWebsocket(roomPin,name);}; const connectDisplay=()=>{if(!roomPin.trim())return alert('PIN gir'); connectWebsocket(roomPin,'DISPLAY');};
  const startGame = async () => {
    playTone(700, 100, 'triangle');

    const result = await startGameRequest(
      roomPin,
      user.token
    );

    if (result.error) {
      alert(result.error);
    }
  };
  const nextQuestion = async () => {
  const result = await nextQuestionRequest(
    roomPin,
    user.token
  );

  if (result.error) {
    alert(result.error);
  }
};

  if(!user) return <div style={styles.splash}><div style={styles.joinCard}><h1>QuizBlast 🚀</h1><h2>{authMode==='login'?'Giriş Yap':'Kayıt Ol'}</h2><input placeholder="E-posta" value={authEmail} onChange={e=>setAuthEmail(e.target.value)} style={styles.input}/><input placeholder="Şifre" type="password" value={authPassword} onChange={e=>setAuthPassword(e.target.value)} style={styles.input}/><button onClick={authMode==='login'?login:register} style={styles.joinButton}>{authMode==='login'?'Giriş Yap':'Kayıt Ol'}</button><button onClick={()=>setAuthMode(authMode==='login'?'register':'login')} style={{...styles.joinButton,marginTop:10,background:'#333'}}>{authMode==='login'?'Hesap oluştur':'Giriş ekranına dön'}</button></div></div>;
  if(!mode) return <div style={styles.splash}><div style={styles.center}><h1 style={styles.logo}>QuizBlast 🚀</h1><p style={styles.subtitle}>Multiplayer Quiz Platform</p><p>{user.email}</p><button onClick={()=>{setMode('host');loadQuizzes();}} style={styles.mainButton}>🎤 Host Game</button><button onClick={()=>setMode('player')} style={styles.mainButton}>🎮 Join Game</button><button onClick={()=>setMode('display')} style={styles.mainButton}>📺 Display Screen</button><button onClick={()=>{setMode('admin');loadQuizzes();}} style={styles.mainButton}>🧠 Admin Panel</button><button onClick={logout} style={{...styles.mainButton,background:'#e21b3c',color:'white'}}>Çıkış Yap</button></div></div>;
  if(mode==='admin') return <AdminView styles={styles} admin={admin} {...{quizzes,selectedQuizId,setSelectedQuizId,selectedQuestions,importExcel,commitImport,importPreview,importing,importSummary,setMode}} />;
  if(reconnecting) return <div style={styles.splash}><div style={styles.center}><h2>Odaya yeniden bağlanılıyor...</h2><button onClick={leaveGame} style={styles.mainButton}>Oyundan Çık</button></div></div>;
  if(mode==='host'&&!joined) return <HostSetup {...{quizzes,selectedQuizId,setSelectedQuizId,loadSelectedQuestions,finalLimit,setFinalLimit,createRoom,selectedQuestions,setMode,styles}} />;
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
          paused={paused}
          questionResult={questionResult}
          optionColors={optionColors}
          visibleLeaderboard={visibleLeaderboard}
          nextQuestion={nextQuestion}
          currentQuestionIndex={currentQuestionIndex}
          totalQuestions={totalQuestions || selectedQuestions.length}
          styles={styles}
        />
      )}
    </div>
  </div>
);
}


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
