import React, { useCallback, useEffect, useRef, useState } from 'react';
import { API, APP_URL } from '../../services/api';
import { useAuth } from '../../hooks/useAuth';
import './poll-host.css';

async function request(path, token, method = 'GET', body) {
  const response = await fetch(API + path, {
    method,
    headers: { Authorization: 'Bearer ' + token, ...(body ? { 'Content-Type': 'application/json' } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(typeof data.detail === 'string' ? data.detail : 'request_failed');
    error.status = response.status;
    throw error;
  }
  return data;
}
const describe = error => ({
  invalid_authentication_credentials: 'Oturum geçersiz. Yeniden giriş yapın.',
  poll_session_not_found: 'Anket oturumu bulunamadı veya erişim yetkiniz yok.',
  poll_session_closed: 'Anket daha önce kapatılmış.',
}[error?.message] || 'İşlem başarısız oldu. Bağlantınızı kontrol edip tekrar deneyin.');

export default function PollHost() {
  const { user } = useAuth();
  const [polls, setPolls] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [question, setQuestion] = useState('');
  const [optionText, setOptionText] = useState('Evet\nHayır');
  const [session, setSession] = useState(null);
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const pollingRef = useRef(false);
  const busyRef = useRef(false);
  const key = user?.email ? 'qb_poll_host_' + user.email : null;

  const refresh = useCallback(async (sessionId, silent = false) => {
    if (!user?.token || !sessionId || pollingRef.current) return;
    pollingRef.current = true;
    try {
      const next = await request('/poll-sessions/' + sessionId + '/results', user.token);
      setResults(next);
      setSession(previous => previous?.session_id === sessionId
        ? { ...previous, status: next.status } : previous);
      if (!silent) setError('');
    } catch (reason) {
      setError(describe(reason));
    } finally {
      pollingRef.current = false;
    }
  }, [user?.token]);

  useEffect(() => {
    if (!user?.token) { setLoading(false); return; }
    let cancelled = false;
    async function bootstrap() {
      try {
        const list = await request('/polls?limit=50', user.token);
        if (cancelled) return;
        setPolls(list.items);
        setSelectedId(list.items[0]?.id || '');
        const saved = key ? JSON.parse(localStorage.getItem(key) || 'null') : null;
        if (saved?.session_id && /^[a-f0-9]{32}$/.test(saved.session_id)) {
          setSession(saved);
          await refresh(saved.session_id);
        }
      } catch (reason) {
        if (!cancelled) setError(describe(reason));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    bootstrap();
    return () => { cancelled = true; };
  }, [user?.token, key, refresh]);

  useEffect(() => {
    if (!session?.session_id || !user?.token || session.status === 'closed') return;
    const timer = window.setInterval(() => {
      if (!document.hidden) refresh(session.session_id, true);
    }, 2500);
    return () => window.clearInterval(timer);
  }, [session?.session_id, session?.status, user?.token, refresh]);

  async function action(work) {
    if (!user?.token || busyRef.current) return;
    busyRef.current = true; setBusy(true); setError('');
    try { await work(); } catch (reason) { setError(describe(reason)); }
    finally { busyRef.current = false; setBusy(false); }
  }
  async function createPoll(event) {
    event.preventDefault();
    const options = optionText.split('\n').map(x => x.trim()).filter(Boolean);
    await action(async () => {
      const poll = await request('/polls', user.token, 'POST', { question: question.trim(), options });
      setPolls(previous => [poll, ...previous]); setSelectedId(poll.id);
      setQuestion('');
    });
  }
  async function openSession() {
    if (!selectedId) return;
    await action(async () => {
      const created = await request('/polls/' + selectedId + '/sessions', user.token, 'POST');
      const saved = { ...created, poll_id: selectedId };
      if (key) localStorage.setItem(key, JSON.stringify(saved));
      setSession(saved); setResults(null);
      await refresh(created.session_id);
    });
  }
  async function closeSession() {
    if (!session?.session_id || !window.confirm('Anket kapatılsın mı? Yeni oylar kabul edilmeyecek.')) return;
    await action(async () => {
      await request('/poll-sessions/' + session.session_id + '/close', user.token, 'POST');
      setSession(previous => ({ ...previous, status: 'closed' }));
      await refresh(session.session_id);
    });
  }
  function clearSession() {
    if (key) localStorage.removeItem(key);
    setSession(null); setResults(null); setError('');
  }
  const link = session?.invite ? APP_URL + '/?poll=' + encodeURIComponent(session.invite) : '';
  const displayLink = session?.display_key ? APP_URL + '/#poll-display=' + encodeURIComponent(session.session_id) + '&key=' + encodeURIComponent(session.display_key) : '';
  if (!user) return <main className="qb-poll-host"><section className="qb-poll-host__panel">
    <h1>Poll Studio</h1><p>Host işlemleri için hesabınızla giriş yapmalısınız.</p>
    <a href="/">Giriş ekranına dön</a>
  </section></main>;

  return <main className="qb-poll-host"><div className="qb-poll-host__layout">
    <header className="qb-poll-host__header">
      <div><small>QuizBlast · Poll Studio</small><h1>Canlı anket yönetimi</h1></div>
      <a href="/">Ana menü</a>
    </header>
    {error && <p role="alert" className="qb-poll-host__error">{error}</p>}
    {loading ? <p role="status">Anketler yükleniyor…</p> : <div className="qb-poll-host__columns">
      <section className="qb-poll-host__panel">
        <h2>Anket başlat</h2>
        <label>Hazır anket
          <select value={selectedId} onChange={e => setSelectedId(e.target.value)}>
            <option value="">Anket seçin</option>
            {polls.map(p => <option key={p.id} value={p.id}>{p.question}</option>)}
          </select>
        </label>
        <button type="button" disabled={!selectedId || busy || session?.status === 'open'}
          onClick={openSession}>Yeni anket oturumu aç</button>
        <form onSubmit={createPoll}>
          <h3>Yeni anket oluştur</h3>
          <label>Soru
            <input value={question} maxLength={500} onChange={e => setQuestion(e.target.value)} required />
          </label>
          <label>Seçenekler (her satıra bir seçenek, 2–6)
            <textarea rows={5} value={optionText} onChange={e => setOptionText(e.target.value)} required />
          </label>
          <button disabled={busy || !question.trim()} type="submit">Anketi kaydet</button>
        </form>
      </section>
      <section className="qb-poll-host__panel" aria-label="Canlı anket sonuçları">
        <div className="qb-poll-host__row">
          <h2>Canlı sonuçlar</h2>
          <span className="qb-poll-host__state">{results?.status === 'closed' ? 'Kapalı' : session ? 'Açık' : 'Oturum yok'}</span>
        </div>
        {!session ? <p>Başlamak için bir anket oturumu açın.</p> : <>
          {link && <div className="qb-poll-host__invite">
            <label>Katılım bağlantısı <input value={link} readOnly aria-label="Katılım bağlantısı" /></label>
            <button type="button" onClick={() => navigator.clipboard?.writeText(link)}>Bağlantıyı kopyala</button>
            {displayLink && <div className="qb-poll-host__display-link">
              <label>Display bağlantısı (salt okunur)
                <input readOnly value={displayLink} aria-label="Display bağlantısı" />
              </label>
              <button type="button" onClick={() => navigator.clipboard?.writeText(displayLink)}>Display bağlantısını kopyala</button>
              <a href={displayLink} target="_blank" rel="noreferrer">Display aç</a>
            </div>}
          </div>}
          {results ? <>
            <h3>{results.question}</h3>
            <div className="qb-poll-host__metrics">
              <div><strong data-testid="poll-total-votes">{results.total_votes}</strong><small>Geçerli oy</small></div>
              <div><strong data-testid="poll-registered">{results.registered_participants}</strong><small>Kayıtlı katılımcı</small></div>
              <div><strong>{results.response_rate_percent}%</strong><small>Yanıt oranı</small></div>
            </div>
            <p className="qb-poll-host__hint">Yanıt oranı, bu anket oturumuna kayıtlı katılımcılara göredir.</p>
            <div className="qb-poll-host__bars">
              {results.options.map(item => <div key={item.index}>
                <div className="qb-poll-host__row"><span>{item.label}</span><strong>{item.votes} oy · {item.percent}%</strong></div>
                <div className="qb-poll-host__track" role="progressbar" aria-label={item.label}
                  aria-valuemin="0" aria-valuemax="100" aria-valuenow={item.percent}>
                  <div style={{ width: item.percent + '%' }} />
                </div>
              </div>)}
            </div>
          </> : <p role="status">Sonuçlar alınıyor…</p>}
          <div className="qb-poll-host__actions">
            <button type="button" onClick={() => refresh(session.session_id)} disabled={busy}>Yenile</button>
            {session.status !== 'closed'
              ? <button type="button" disabled={busy} onClick={closeSession}>Anketi kapat</button>
              : <button type="button" onClick={clearSession}>Yeni oturuma geç</button>}
          </div>
        </>}
      </section>
    </div>}
  </div></main>;
}
