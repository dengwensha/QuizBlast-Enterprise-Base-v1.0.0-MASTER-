import React, { useEffect, useState } from 'react';
import { getEventAgenda, saveEventAgenda } from '../../services/eventService';

const labels = { presentation: 'Sunum', quiz: 'Quiz', break: 'Ara' };

export default function EventAgenda({ token, eventId, onBack }) {
  const [agenda, setAgenda] = useState(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    getEventAgenda(token, eventId).then(result => {
      if (active) setAgenda(result);
    }).catch(e => {
      if (active) setError(e.message);
    }).finally(() => {
      if (active) setBusy(false);
    });
    return () => { active = false; };
  }, [token, eventId, reload]);

  const steps = agenda?.steps || [];
  const edit = next => { setAgenda({ ...agenda, steps: next }); setSaved(false); };
  const move = (index, direction) => {
    const next = [...steps];
    [next[index], next[index + direction]] = [next[index + direction], next[index]];
    edit(next);
  };
  const submit = async event => {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError(''); setSaved(false);
    try {
      setAgenda(await saveEventAgenda(token, eventId, { revision: agenda.revision, steps }));
      setSaved(true);
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  return <main className="qb-events">
    <header><h1>Etkinlik Programı</h1><button disabled={busy} onClick={onBack}>Etkinliklere Dön</button></header>
    {error && <p role="alert">{error}</p>}
    {error && <button disabled={busy} onClick={() => {
      setBusy(true); setError(''); setSaved(false); setReload(value => value + 1);
    }}>Güncel Programı Yükle</button>}
    {saved && <p role="status">Program kaydedildi.</p>}
    {agenda && <form className="qb-events__panel" onSubmit={submit}>
      <h2>{agenda.title}</h2>
      {!steps.length && <p>Programa bir adım ekle.</p>}
      <ol>{steps.map((step, index) => <li key={index}>
        <label>{labels[step.kind]} başlığı
          <input required maxLength={160} disabled={busy} value={step.title}
            onChange={e => edit(steps.map((item, i) => i === index ? { ...item, title: e.target.value } : item))} />
        </label>
        <div className="qb-events__actions">
          <button type="button" aria-label={`${index + 1}. adımı yukarı taşı`} disabled={busy || !index} onClick={() => move(index, -1)}>Yukarı</button>
          <button type="button" aria-label={`${index + 1}. adımı aşağı taşı`} disabled={busy || index === steps.length - 1} onClick={() => move(index, 1)}>Aşağı</button>
          <button type="button" aria-label={`${index + 1}. adımı kaldır`} disabled={busy} onClick={() => edit(steps.filter((_, i) => i !== index))}>Kaldır</button>
        </div>
      </li>)}</ol>
      <div className="qb-events__actions">
        {Object.entries(labels).map(([kind, title]) => <button key={kind} type="button"
          disabled={busy || steps.length >= 50 || (kind === 'quiz' && steps.some(step => step.kind === kind))}
          onClick={() => edit([...steps, { kind, title }])}>{title} Ekle</button>)}
        <button type="submit" disabled={busy || steps.some(step => !step.title.trim())}>Programı Kaydet</button>
      </div>
    </form>}
  </main>;
}
