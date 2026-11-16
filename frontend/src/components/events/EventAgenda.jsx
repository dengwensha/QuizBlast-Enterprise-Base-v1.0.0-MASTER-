import React, { useEffect, useState } from 'react';
import { getEventAgenda, getEventGame, saveEventAgenda, uploadEventDeck } from '../../services/eventService';

import SlideImage from './SlideImage';
import './event-agenda.css';

const labels = { presentation: 'Sunum', quiz: 'Quiz', break: 'Ara' };

export default function EventAgenda({ token, eventId, onBack }) {
  const [agenda, setAgenda] = useState(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const [preview, setPreview] = useState(null);
  const [page, setPage] = useState(0);
  const [count, setCount] = useState(0);
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
  const quizSteps = steps.filter(step => step.kind === 'quiz');
  const plannedQuizzes = quizSteps.length > 1 || quizSteps.some(step => step.quiz_id);
  const [quizzes, setQuizzes] = useState(null);
  const [catalogError, setCatalogError] = useState('');
  useEffect(() => {
    if (!plannedQuizzes) return;
    let active = true;
    setQuizzes(null);
    setCatalogError('');
    getEventGame(token, eventId).then(result => {
      if (active) setQuizzes(result.quizzes);
    }).catch(e => {
      if (active) setCatalogError(e.message);
    });
    return () => { active = false; };
  }, [token, eventId, plannedQuizzes, reload]);
  const edit = next => { setAgenda({ ...agenda, steps: next }); setSaved(false); };
  const move = (index, direction) => {
    const next = [...steps];
    [next[index], next[index + direction]] = [next[index + direction], next[index]];
    edit(next);
  };
  const upload = async (index, file) => {
    if (!file || busy) return;
    setBusy(true); setError('');
    try {
      const deck = await uploadEventDeck(token, eventId, file);
      edit(steps.map((item, i) => i === index ? { ...item, deck_id: deck.id } : item));
      setPreview(deck.id); setPage(0); setCount(deck.page_count);
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
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

  return <main className="qb-events qb-agenda">
    <header className="qb-agenda__header"><div><h1>Etkinlik Programı</h1><p>Sunum, quiz ve araları etkinlik sırasına göre düzenle.</p></div><button disabled={busy} onClick={onBack}>Etkinliklere Dön</button></header>
    {error && <p role="alert">{error}</p>}
    {error && <button disabled={busy} onClick={() => {
      setBusy(true); setError(''); setSaved(false); setReload(value => value + 1);
    }}>Güncel Programı Yükle</button>}
    {saved && <p role="status">Program kaydedildi.</p>}
    {busy && !agenda && <p role="status">Program yükleniyor…</p>}
    {agenda && <form className="qb-events__panel" onSubmit={submit}>
      <h2>{agenda.title}</h2>
      {plannedQuizzes && <p>Adıma özel quiz seçimleri taslak olarak kaydedilir. Bu program henüz canlı başlatılamaz.</p>}
      {plannedQuizzes && catalogError && <p role="alert">{catalogError}</p>}
      {!steps.length && <p>Programa bir adım ekle.</p>}
      <ol className="qb-agenda__steps">{steps.map((step, index) => <li key={index} className="qb-agenda__step" data-kind={step.kind}>
        <h3><span className="qb-agenda__number">{index + 1}.</span> {labels[step.kind]}</h3>
        <label>{labels[step.kind]} başlığı
          <input required maxLength={160} disabled={busy} value={step.title}
            onChange={e => edit(steps.map((item, i) => i === index ? { ...item, title: e.target.value } : item))} />
        </label>
        {step.kind === 'quiz' && plannedQuizzes && <label>Bu adımın quizi
          <select value={step.quiz_id ?? ''} disabled={busy || !quizzes}
            onChange={e => edit(steps.map((item, i) => i === index
              ? { ...item, quiz_id: e.target.value ? Number(e.target.value) : null } : item))}>
            <option value="">Henüz seçilmedi</option>
            {step.quiz_id && !quizzes?.some(quiz => quiz.id === step.quiz_id) &&
              <option value={step.quiz_id} disabled>{quizzes ? 'Quiz artık erişilebilir değil' : 'Quizler yükleniyor…'}</option>}
            {quizzes?.map(quiz => <option key={quiz.id} value={quiz.id} disabled={!quiz.question_count}>
              {quiz.title} ({quiz.question_count} soru)
            </option>)}
          </select>
        </label>}
        {step.kind === 'presentation' && <div className="qb-agenda__pdf">
          <label>{step.deck_id ? "PDF’yi değiştir" : "PDF yükle"}<input type="file" accept="application/pdf,.pdf" disabled={busy}
            onChange={e => { const file = e.target.files?.[0]; e.target.value = ''; upload(index, file); }} /></label>
          {step.deck_id && <button type="button" disabled={busy} onClick={() => {
            setPreview(step.deck_id); setPage(0); setCount(0);
          }}>PDF Önizle</button>}
        </div>}
        <div className="qb-events__actions qb-agenda__tools">
          <button type="button" aria-label={`${index + 1}. adımı yukarı taşı`} disabled={busy || !index} onClick={() => move(index, -1)}>Yukarı</button>
          <button type="button" aria-label={`${index + 1}. adımı aşağı taşı`} disabled={busy || index === steps.length - 1} onClick={() => move(index, 1)}>Aşağı</button>
          <button type="button" aria-label={`${index + 1}. adımı kaldır`} disabled={busy} onClick={() => edit(steps.filter((_, i) => i !== index))}>Kaldır</button>
        </div>
      </li>)}</ol>
      <div className="qb-events__actions qb-agenda__footer">
        {Object.entries(labels).map(([kind, title]) => <button key={kind} type="button"
          disabled={busy || steps.length >= 50}
          onClick={() => edit([...steps, { kind, title }])}>{title} Ekle</button>)}
        <button type="submit" disabled={busy || steps.some(step => !step.title.trim())}>Programı Kaydet</button>
      </div>
    </form>}
    {preview && <section className="qb-events__panel">
      <h2>PDF Önizleme</h2>
      <SlideImage key={`${preview}:${page}`} token={token} path={`/${eventId}/decks/${preview}/${page}`} onCount={setCount} />
      <div className="qb-events__actions qb-agenda__tools"><button disabled={!page} onClick={() => setPage(page - 1)}>Önceki Slayt</button>
      <button disabled={page + 1 >= count} onClick={() => setPage(page + 1)}>Sonraki Slayt</button>
      <button onClick={() => setPreview(null)}>Önizlemeyi Kapat</button></div>
    </section>}
  </main>;
}
