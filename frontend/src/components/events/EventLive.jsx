import React, { useEffect, useState } from 'react';
import { advanceEventLive, getEventDisplay, getEventLive, startEventLive } from '../../services/eventService';
import './event-studio.css';
import './event-live.css';
import SlideImage from './SlideImage';
import EventReport from './EventReport';
import StageViewport from '../game/StageViewport';

const labels = { presentation: 'Sunum', quiz: 'Quiz', break: 'Ara' };

function StepTitle({ step }) {
  return <>{step.kind === 'break' && <span aria-hidden="true">☕{' '}</span>}{step.title}</>;
}

function Program({ live, displayKey, onReport }) {
  const step = live.steps[live.cursor];
  const showing = live.view === 'step' && step;
  const total = live.steps.length;
  const completed = Math.min(live.cursor, total);
  return <section className="qb-events__panel qb-live__program">
    <div className="qb-live__summary">
      <p className="qb-live__eyebrow">{showing ? labels[step.kind] : step ? 'Sıradaki adım' : 'Etkinlik sona erdi'}</p>
      <h2>{step ? <StepTitle step={step} /> : 'Program tamamlandı'}</h2>
      {total > 0 && <div className="qb-live__progress">
        <span>{completed} / {total} adım tamamlandı</span>
        <progress aria-label="Program ilerlemesi" value={completed} max={total} />
      </div>}
    </div>
    {showing ? (!!live.page_count && <div className="qb-live__slide">
      <p>Slayt {live.page + 1} / {live.page_count}</p>
      <SlideImage key={`${live.revision}:${live.page}`} token={displayKey} path={`/display/program/page/${live.revision}?requested_page=${live.page}`} />
    </div>) : <ol className="qb-live__timeline">{live.steps.map((item, i) => {
      const status = i < live.cursor ? 'Tamamlandı' : i === live.cursor ? 'Sırada' : 'Bekliyor';
      return <li key={i} data-kind={item.kind} aria-current={i === live.cursor ? 'step' : undefined} data-complete={i < live.cursor}>
        <span className="qb-live__number" aria-hidden="true">{i + 1}</span>
        <div><strong><StepTitle step={item} /></strong><small>{labels[item.kind]}</small>
          {onReport && item.quiz_id && i < live.cursor &&
            <button onClick={() => onReport(item.step_id)}>Quiz Raporu</button>}
        </div>
        <span className="qb-live__status">{status}</span>
      </li>;
    })}</ol>}
  </section>;
}

export function EventLiveDisplay({ displayKey, renderQuiz }) {
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
  if (!error && live?.quiz_display) return renderQuiz(live.quiz_display);
  return <StageViewport enabled><main className="qb-events qb-live qb-live--display">
    <header className="qb-live__header"><div><p className="qb-live__eyebrow">Etkinlik Programı</p><h1>{live?.title || 'Canlı Etkinlik'}</h1></div></header>
    {error ? <p role="alert">Program bağlantısı kurulamadı. Yeniden deneniyor.</p>
      : live ? <Program live={live} displayKey={displayKey} /> : <p role="status">Program yükleniyor…</p>}
  </main></StageViewport>;
}

export default function EventLive({ token, eventId, onBack, onQuiz }) {
  const [data, setData] = useState(null);
  const [reportStep, setReportStep] = useState(null);
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
  const automatic = live?.view === 'step' && !!step?.slide_seconds;
  const playing = automatic && live.page + 1 < live.page_count;
  useEffect(() => {
    if (!playing || busy) return;
    let active = true;
    let timer;
    async function refresh() {
      try {
        const next = await getEventLive(token, eventId);
        if (active) { setData(next); setError(''); }
      } catch (e) { if (active) setError(e.message); }
      finally { if (active) timer = setTimeout(refresh, 1000); }
    }
    timer = setTimeout(refresh, 1000);
    return () => { active = false; clearTimeout(timer); };
  }, [playing, busy, token, eventId]);
  const command = action => perform(() => advanceEventLive(token, eventId, { action, revision: live.revision }));
  // Presentation remotes commonly emulate these four keyboard keys.
  useEffect(() => {
    if (reportStep || automatic || live?.view !== 'step' ||
        step?.kind !== 'presentation' || !live.page_count) return;
    function onKey(event) {
      if (event.defaultPrevented || event.isComposing || event.altKey || event.ctrlKey ||
          event.metaKey || event.shiftKey || event.target?.isContentEditable ||
          event.target?.closest?.('input, textarea, select, [role="textbox"], [role="slider"]')) return;
      const forward = event.key === 'PageDown' || event.key === 'ArrowRight';
      if (!forward && event.key !== 'PageUp' && event.key !== 'ArrowLeft') return;
      event.preventDefault();
      if (busy || event.repeat || (forward ? live.page + 1 >= live.page_count : live.page <= 0)) return;
      command(forward ? 'next_page' : 'previous_page');
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });
  if (reportStep) return <EventReport token={token} eventId={eventId} stepId={reportStep} onBack={() => setReportStep(null)} />;
  return <StageViewport enabled><main className="qb-events qb-live">
    <header className="qb-live__header"><div><p className="qb-live__eyebrow">Event Studio</p><h1>Canlı Etkinlik</h1>{live?.title && <p>{live.title}</p>}</div><button disabled={busy} onClick={onBack}>Etkinliklere Dön</button></header>
    {error && <p role="alert">{error}</p>}
    {!live && <button disabled={busy} onClick={() => perform(() => startEventLive(token, eventId))}>Programı Başlat</button>}
    {live && <>
      <Program live={live} displayKey={data.display_key} onReport={setReportStep} />
      <div className="qb-events__actions">
        <a className="qb-live__display-link" target="_blank" rel="noopener noreferrer" href={`/#event-display=${data.display_key}`}>Program Display’ini Aç</a>
        {step && live.view === 'agenda' && <button disabled={busy} onClick={() => command('open')}>Sonraki Adımı Aç</button>}
        {live.view === 'step' && <>
          {automatic && <p>{playing ? `Slaytlar ${step.slide_seconds} saniyede bir ilerler.` : 'Son slayt. Sunum burada bekler.'}</p>}
          {!!live.page_count && !automatic && <>
            <small>Sunum kumandası: Host penceresinde ← / → veya Page Up / Page Down.</small>
            <button disabled={busy || !live.page} onClick={() => command('previous_page')}>Önceki Slayt</button>
            <button disabled={busy || live.page + 1 >= live.page_count} onClick={() => command('next_page')}>Sonraki Slayt</button>
          </>}
          {step?.kind === 'quiz' && <button disabled={busy} onClick={() => onQuiz(step)}>Quiz ve Oturuma Git</button>}
          <button disabled={busy} onClick={() => command('complete')}>Adımı Bitir ve Programa Dön</button>
        </>}
        <button disabled={busy} onClick={() => perform(() => getEventLive(token, eventId))}>Güncel Durumu Yükle</button>
      </div>
    </>}
  </main></StageViewport>;
}
