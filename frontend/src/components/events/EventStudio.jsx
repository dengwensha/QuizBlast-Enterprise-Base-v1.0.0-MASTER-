import React, { useEffect, useRef, useState } from 'react';
import { copyEvent, getEvent, listEvents, saveEvent } from '../../services/eventService';
import EventLive from './EventLive';
import EventAgenda from './EventAgenda';
import EventGameSetup from './EventGameSetup';
import './event-studio.css';

const statusLabels = { draft: 'Taslak', ready: 'Hazır', lobby: 'Oyuncular bekleniyor', question: 'Oyun sürüyor', result: 'Soru sonucu', leaderboard: 'Sıralama', completed: 'Tamamlandı', closed: 'Oda kapalı' };
const blank = () => ({ title: '', organization: '', scheduled_at: '' });
const localInput = value => {
  if (!value) return '';
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
};

export default function EventStudio({ user, onBack, onOpenHost, onOpenDisplay }) {
  const [liveEvent, setLiveEvent] = useState(null);
  const [agendaEvent, setAgendaEvent] = useState(null);
  const [gameEvent, setGameEvent] = useState(null);
  const [items, setItems] = useState([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState('');
  const [editor, setEditor] = useState(null);
  const [form, setForm] = useState(blank);
  const [saving, setSaving] = useState(false);
  const savingRef = useRef(false);
  const requestRef = useRef(0);

  const load = async () => {
    const current = ++requestRef.current;
    setLoading(true); setError('');
    try {
      const result = await listEvents(user.token, offset);
      if (current !== requestRef.current) return;
      setItems(result.items); setHasMore(result.has_more);
    } catch (e) { if (current === requestRef.current) setError(e.message); }
    finally { if (current === requestRef.current) setLoading(false); }
  };
  useEffect(() => { load(); return () => { requestRef.current += 1; }; }, [user.token, offset]);

  const open = async id => {
    setFeedback(''); setError('');
    if (!id) { setEditor({}); setForm(blank()); return; }
    setLoading(true);
    try {
      const row = await getEvent(user.token, id);
      setEditor(row);
      setForm({ title: row.title, organization: row.organization || '', scheduled_at: localInput(row.scheduled_at) });
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };
  const submit = async e => {
    e.preventDefault();
    if (savingRef.current) return;
    savingRef.current = true; setSaving(true); setError(''); setFeedback('');
    try {
      const data = { title: form.title.trim(), organization: form.organization.trim() || null,
        scheduled_at: form.scheduled_at ? new Date(form.scheduled_at).toISOString() : null };
      if (editor.id) data.revision = editor.revision;
      await saveEvent(user.token, editor.id, data);
      setEditor(null); setFeedback('Etkinlik taslağı kaydedildi.');
      if (offset) setOffset(0); else await load();
    } catch (e) { setError(e.message); }
    finally { savingRef.current = false; setSaving(false); }
  };
  const duplicate = async id => {
    if (savingRef.current) return;
    savingRef.current = true; setSaving(true); setError(''); setFeedback('');
    try {
      const { event } = await copyEvent(user.token, id);
      setFeedback(`“${event.title}” oluşturuldu.`);
      if (offset) setOffset(0); else await load();
    } catch (e) { setError(e.message); }
    finally { savingRef.current = false; setSaving(false); }
  };
  if (agendaEvent) return <EventAgenda token={user.token} eventId={agendaEvent} onBack={() => { setAgendaEvent(null); load(); }} />;
  if (gameEvent) return <EventGameSetup user={user} eventId={gameEvent} onBack={() => { setGameEvent(null); load(); }} onOpenHost={onOpenHost} onOpenDisplay={onOpenDisplay} />;
  if (liveEvent) return <EventLive token={user.token} eventId={liveEvent}
    onBack={() => setLiveEvent(null)} onQuiz={() => setGameEvent(liveEvent)} />;
  return <main className="qb-events">
    <header><div><p>QUIZBLAST EVENT STUDIO</p><h1>Etkinliklerim</h1></div>
      <button onClick={onBack} disabled={saving}>Ana Menü</button></header>
    <p>Etkinliğini planla ve taslak bilgilerini düzenle.</p>
    {error && <p role="alert">{error}</p>}
    {feedback && <p role="status">{feedback}</p>}
    {editor ? <form onSubmit={submit} className="qb-events__panel">
      <h2>{editor.id ? 'Etkinliği Düzenle' : 'Yeni Etkinlik'}</h2>
      <label>Etkinlik başlığı<input required maxLength={160} value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} disabled={saving} /></label>
      <label>Kurum adı (isteğe bağlı)<input maxLength={160} value={form.organization} onChange={e => setForm({ ...form, organization: e.target.value })} disabled={saving} /></label>
      <label>Planlanan tarih (isteğe bağlı)<input type="datetime-local" value={form.scheduled_at} onChange={e => setForm({ ...form, scheduled_at: e.target.value })} disabled={saving} /></label>
      <small>Tarih, bu cihazın saat dilimine göre gösterilir.</small>
      <div className="qb-events__actions"><button type="submit" disabled={saving || !form.title.trim()}>{saving ? 'Kaydediliyor…' : 'Kaydet'}</button>
        <button type="button" disabled={saving} onClick={() => { setEditor(null); setError(''); }}>Vazgeç</button>
        {editor.id && <button type="button" disabled={saving} onClick={() => open(editor.id)}>Güncel Kaydı Aç</button>}</div>
    </form> : <>
      <button onClick={() => open()} disabled={loading}>Etkinlik Oluştur</button>
      {loading ? <p role="status">Etkinlikler yükleniyor…</p> : error ? <button onClick={load}>Tekrar Dene</button> : <>
        {!items.length && <p>Henüz etkinlik taslağı yok.</p>}
        <div className="qb-events__grid">{items.map(row => <article key={row.id} className="qb-events__panel">
          <span>{statusLabels[row.status] || row.status}</span><h2>{row.title}</h2>{row.organization && <p>{row.organization}</p>}
          <p>{row.scheduled_at ? new Date(row.scheduled_at).toLocaleString('tr-TR') : 'Tarih belirlenmedi'}</p>
          <button aria-label={`Quiz ve Oturum: ${row.title}`} onClick={() => setGameEvent(row.id)}>Quiz ve Oturum</button>
          <button disabled={saving} aria-label={`Canlı Etkinlik: ${row.title}`} onClick={() => setLiveEvent(row.id)}>Canlı Etkinlik</button>
          <button disabled={saving} aria-label={`Program: ${row.title}`} onClick={() => setAgendaEvent(row.id)}>Program</button>
          <button disabled={saving} aria-label={`Kopyala: ${row.title}`} onClick={() => duplicate(row.id)}>Kopyala</button>
          <button aria-label={`Düzenle: ${row.title}`} onClick={() => open(row.id)}>Düzenle</button>
        </article>)}</div>
        <nav aria-label="Etkinlik sayfaları" className="qb-events__actions"><button disabled={!offset} onClick={() => setOffset(offset - 20)}>Önceki</button><button disabled={!hasMore} onClick={() => setOffset(offset + 20)}>Sonraki</button></nav>
      </>}
    </>}
  </main>;
}
