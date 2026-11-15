import React, { useEffect, useState } from 'react';
import { advanceEventLive, getEventDisplay, getEventLive, startEventLive } from '../../services/eventService';
import './event-studio.css';
import SlideImage from './SlideImage';

const labels = { presentation: 'Sunum', quiz: 'Quiz', break: 'Ara' };

function Program({ live, displayKey }) {
  const step = live.steps[live.cursor];
  if (live.view === 'step' && step) return <section className="qb-events__panel">
    <p>{labels[step.kind]}</p><h2>{step.title}</h2>
    {!!live.page_count && <><p>Slayt {live.page + 1} / {live.page_count}</p>
      <SlideImage key={live.revision} token={displayKey} path={`/display/program/page/${live.revision}`} /></>}
  </section>;
  return <section className="qb-events__panel">
    <h2>{step ? `Sırada: ${step.title}` : 'Program tamamlandı'}</h2>
    <ol>{live.steps.map((item, i) => <li key={i}>
      {item.title} · {i < live.cursor ? 'Tamamlandı' : i === live.cursor ? 'Sırada' : labels[item.kind]}
    </li>)}</ol>
  </section>;
}

export function EventLiveDisplay({ displayKey }) {
  const [live, setLive] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    let timer;
    const refresh = async () => {
      try {
        const state = await getEventDisplay(displayKey);
        if (active) { setLive(state); setError(''); }
      } catch (e) {
        if (active) setError(e.message);
      } finally {
        if (active) timer = setTimeout(refresh, 1000);
      }
    };
    refresh();
    return () => { active = false; clearTimeout(timer); };
  }, [displayKey]);
  return <main className="qb-events">
    <h1>{live?.title || 'Etkinlik Programı'}</h1>
    {error ? <p role="alert">Program bağlantısı kurulamadı. Yeniden deneniyor.</p>
      : live ? <Program live={live} displayKey={displayKey} /> : <p role="status">Program yükleniyor…</p>}
  </main>;
}

export default function EventLive({ token, eventId, onBack, onQuiz }) {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    getEventLive(token, eventId).then(value => {
      if (active) setData(value);
    }).catch(e => {
      if (active) setError(e.message);
    }).finally(() => {
      if (active) setBusy(false);
    });
    return () => { active = false; };
  }, [token, eventId]);
  const perform = async action => {
    setBusy(true); setError('');
    try { setData(await action()); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };
  const live = data?.live;
  const step = live?.steps[live.cursor];
  const command = action => perform(() => advanceEventLive(token, eventId, { action, revision: live.revision }));
  return <main className="qb-events">
    <header><h1>Canlı Etkinlik</h1><button disabled={busy} onClick={onBack}>Etkinliklere Dön</button></header>
    {error && <p role="alert">{error}</p>}
    {!live && <button disabled={busy} onClick={() => perform(() => startEventLive(token, eventId))}>Programı Başlat</button>}
    {live && <>
      <Program live={live} displayKey={data.display_key} />
      <div className="qb-events__actions">
        <a target="_blank" rel="noopener noreferrer" href={`/#event-display=${data.display_key}`}>Program Display’ini Aç</a>
        {step && live.view === 'agenda' && <button disabled={busy} onClick={() => command('open')}>Sonraki Adımı Aç</button>}
        {live.view === 'step' && <>
          {!!live.page_count && <>
            <button disabled={busy || !live.page} onClick={() => command('previous_page')}>Önceki Slayt</button>
            <button disabled={busy || live.page + 1 >= live.page_count} onClick={() => command('next_page')}>Sonraki Slayt</button>
          </>}
          {step?.kind === 'quiz' && <button disabled={busy} onClick={onQuiz}>Quiz ve Oturuma Git</button>}
          <button disabled={busy} onClick={() => command('complete')}>Adımı Bitir ve Programa Dön</button>
        </>}
        <button disabled={busy} onClick={() => perform(() => getEventLive(token, eventId))}>Güncel Durumu Yükle</button>
      </div>
    </>}
  </main>;
}
