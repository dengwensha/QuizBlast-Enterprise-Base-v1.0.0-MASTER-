import React, { useEffect, useRef, useState } from 'react';
import { createEventSession, getEventGame, selectEventQuiz } from '../../services/eventService';
import EventReport from './EventReport';
import InvitationShare from '../game/InvitationShare';
import JoinQrPopup from '../game/JoinQrPopup';
import { APP_URL } from '../../services/api';

const phases = { lobby: 'Oyuncular bekleniyor', question: 'Oyun sürüyor', result: 'Soru sonucu', leaderboard: 'Sıralama', completed: 'Tamamlandı', closed: 'Oda kapalı' };

export default function EventGameSetup({ user, eventId, onBack, onOpenHost, onOpenDisplay }) {
  const [showReport, setShowReport] = useState(false);
  const [state, setState] = useState(null);
  const [choice, setChoice] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const busyRef = useRef(false);
  const mounted = useRef(true);
  const load = async () => {
    busyRef.current = true; setBusy(true); setError('');
    try {
      const result = await getEventGame(user.token, eventId);
      if (mounted.current) { setState(result); setChoice(String(result.quiz_id || '')); }
    } catch (e) { if (mounted.current) setError(e.message); }
    finally { busyRef.current = false; if (mounted.current) setBusy(false); }
  };
  useEffect(() => { mounted.current = true; load(); return () => { mounted.current = false; }; }, [user.token, eventId]);
  const perform = async action => {
    if (busyRef.current) return;
    busyRef.current = true; setBusy(true); setError('');
    try {
      const result = await action();
      if (mounted.current) { setState(previous => ({ ...previous, ...result })); setChoice(String(result.quiz_id || '')); }
    } catch (e) { if (mounted.current) setError(e.message); }
    finally { busyRef.current = false; if (mounted.current) setBusy(false); }
  };
  const session = state?.session;
  const joinUrl = session ? `${APP_URL}?pin=${session.pin}` : null;
  if (showReport) return <EventReport token={user.token} eventId={eventId} onBack={() => setShowReport(false)} />;
  return <main className="qb-events">
    <header><h1>Quiz ve Oturum</h1><button disabled={busy} onClick={onBack}>Etkinliklere Dön</button></header>
    {error && <p role="alert">{error}</p>}
    {busy && <p role="status">İşlem sürüyor…</p>}
    <button disabled={busy} onClick={load}>Güncel Durumu Yenile</button>
    {state && <section className="qb-events__panel">
      <h2>{state.event.title}</h2>
      {!session ? <>
        <label>Etkinlik quizi<select value={choice} disabled={busy} onChange={e => setChoice(e.target.value)}>
          <option value="">Quiz seç</option>
          {state.quizzes.map(q => <option key={q.id} value={String(q.id)} disabled={!q.question_count}>{q.title} ({q.question_count} soru)</option>)}
        </select></label>
        {!state.quizzes.length && <p>Önce Admin Panelinde quiz oluştur veya hazır quizleri kontrol et.</p>}
        <div className="qb-events__actions">
          <button disabled={busy || !choice || choice === String(state.quiz_id || '')} onClick={() => perform(() => selectEventQuiz(user.token, eventId, Number(choice), state.event.revision))}>Quiz Seçimini Kaydet</button>
          <button disabled={busy || !state.quiz_id || choice !== String(state.quiz_id)} onClick={() => perform(() => createEventSession(user.token, eventId, state.event.revision))}>Oturum Oluştur</button>
        </div>
        <p>Oturum oluşturmak oyunu başlatmaz. Oturum oluşturulduktan sonra quiz değiştirilemez.</p>
      </> : <>
        <p role="status">{phases[session.phase] || session.phase}</p>
        <p>Quiz: {state.quizzes.find(q => q.id === session.quiz_id)?.title || `#${session.quiz_id}`}</p>
        {['completed', 'closed'].includes(session.phase) && <button onClick={() => setShowReport(true)}>Etkinlik Raporu</button>}
        {session.can_open ? <>
          <p>PIN: <strong>{session.pin}</strong></p>
          {session.phase === 'lobby' && <InvitationShare key={session.instance_id} roomPin={session.pin} joinUrl={joinUrl} />}
          <JoinQrPopup roomPin={session.pin} joinUrl={joinUrl} />
          <div className="qb-events__actions"><button disabled={busy} onClick={() => onOpenHost(session)}>Host Ekranını Aç</button><button disabled={busy} onClick={() => onOpenDisplay(session)}>Display Ekranını Aç</button></div>
        </> : <p>Bu oturum kapatılmış. Yeni bir oyun için yeni etkinlik oluştur.</p>}
      </>}
    </section>}
  </main>;
}
