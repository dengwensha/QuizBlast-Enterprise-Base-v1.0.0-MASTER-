import React, { useEffect, useState } from 'react';
import { slideRemoteState, moveRemoteSlide } from '../../services/eventService';

export default function SlideRemote({ id, accessKeyValue }) {
  const [slide, setSlide] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    if (busy) return;
    let active = true;
    let timer;
    async function read() {
      try {
        const value = await slideRemoteState(accessKeyValue, id);
        if (active) { setSlide(value); setError(''); }
      } catch (e) {
        if (active) { setSlide(null); setError(e.message); }
      } finally { if (active) timer = setTimeout(read, 1500); }
    }
    read();
    return () => { active = false; clearTimeout(timer); };
  }, [id, accessKeyValue, busy]);
  async function move(action) {
    setBusy(true);
    try { setSlide(await moveRemoteSlide(accessKeyValue, id, action, slide.revision)); }
    catch (e) { setSlide(null); setError(e.message); }
    finally { setBusy(false); }
  }
  return <main className="qb-events"><h1>Slayt kumandası</h1>
    {error && <p role="alert">{error}</p>}
    <p aria-live="polite">{slide ? `Slayt ${slide.page + 1} / ${slide.page_count}` : !error && 'Bağlanıyor…'}</p>
    <div className="qb-events__actions">
      <button disabled={busy || !slide?.page} onClick={() => move('previous_page')}>← Önceki</button>
      <button disabled={busy || !slide || slide.page + 1 >= slide.page_count} onClick={() => move('next_page')}>Sonraki →</button>
    </div></main>;
}
