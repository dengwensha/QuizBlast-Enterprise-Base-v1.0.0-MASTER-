import React, { useEffect, useState } from 'react';
import { API } from '../../services/api';
import './poll-display.css';

export default function PollDisplay({ sessionId, accessKey }) {
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    if (!/^[a-f0-9]{32}$/.test(sessionId || '') ||
        !/^[A-Za-z0-9_-]{43}$/.test(accessKey || '')) {
      setError('Display bağlantısı geçersiz.');
      return;
    }
    let stopped = false;
    let busy = false;
    async function load() {
      if (busy || stopped) return;
      busy = true;
      try {
        const response = await fetch(API + '/poll-sessions/' + sessionId + '/display-results', {
          headers: { Authorization: 'Bearer ' + accessKey },
          cache: 'no-store',
        });
        if (!response.ok) throw new Error(response.status === 404 ? 'Display yetkisi geçersiz.' : 'Sonuçlara bağlanılamadı.');
        const next = await response.json();
        if (!stopped) { setResult(next); setError(''); }
      } catch (reason) {
        if (!stopped) setError(reason.message);
      } finally {
        busy = false;
      }
    }
    load();
    const timer = window.setInterval(load, 2500);
    const onVisible = () => { if (!document.hidden) load(); };
    document.addEventListener('visibilitychange', onVisible);
    return () => { stopped = true; window.clearInterval(timer); document.removeEventListener('visibilitychange', onVisible); };
  }, [sessionId, accessKey]);

  return <main className="qb-poll-display">
    <div className="qb-poll-display__shell">
      <header><div className="qb-poll-display__brand">QuizBlast · Poll Studio</div>
        <span className="qb-poll-display__status">{result?.status === 'closed' ? 'Anket tamamlandı' : 'Canlı anket'}</span>
      </header>
      {result ? <>
        <h1>{result.question}</h1>
        <p className="qb-poll-display__total">Toplam geçerli oy: <strong data-testid="poll-display-total">{result.total_votes}</strong></p>
        <div className="qb-poll-display__bars">
          {result.options.map(option => <div className="qb-poll-display__option" key={option.index}>
            <div className="qb-poll-display__label"><span>{option.label}</span>
              <strong>{option.votes} oy · {option.percent}%</strong></div>
            <div className="qb-poll-display__track" role="progressbar" aria-label={option.label}
              aria-valuemin="0" aria-valuemax="100" aria-valuenow={option.percent}>
              <div style={{ width: option.percent + '%' }} />
            </div>
          </div>)}
        </div>
        <footer>Yanıtlayan: {result.total_votes} / {result.registered_participants} kayıtlı katılımcı
          {result.status === 'closed' ? ' · Son sonuçlar' : ''}</footer>
      </> : <p role="status">Sonuçlara bağlanılıyor…</p>}
      {error && <p role="alert">{error}</p>}
    </div>
  </main>;
}
