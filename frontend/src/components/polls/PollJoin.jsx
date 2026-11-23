import React, { useEffect, useRef, useState } from 'react';
import { API } from '../../services/api';
import './poll-join.css';

// This page intentionally runs outside the Quiz/WebSocket and sign-in flows.
function readStored(invite) {
  try { return JSON.parse(localStorage.getItem('qb_poll_join_' + invite) || 'null'); }
  catch { return null; }
}
function saveStored(invite, state) {
  localStorage.setItem('qb_poll_join_' + invite, JSON.stringify(state));
}
async function callApi(path, options) {
  const response = await fetch(API + path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(typeof data.detail === 'string' ? data.detail : 'request_failed');
    error.status = response.status;
    throw error;
  }
  return data;
}
const messageFor = (error) => ({
  poll_invite_not_found: 'Anket bağlantısı geçersiz veya anket kapalı.',
  poll_session_closed: 'Bu anket için oy verme sona erdi.',
  poll_vote_already_cast: 'Oyunuz kaydedildi; değiştiremezsiniz.',
  poll_participant_unauthorized: 'Katılımcı oturumunuz doğrulanamadı.',
  poll_option_invalid: 'Geçerli bir seçenek belirleyin.',
}[error?.message] || 'İşlem tamamlanamadı. Bağlantınızı kontrol edip tekrar deneyin.');

export default function PollJoin({ invite }) {
  const [poll, setPoll] = useState(null);
  const [participant, setParticipant] = useState(null);
  const [receipt, setReceipt] = useState(null);
  const [status, setStatus] = useState('loading');
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState('');
  const joining = useRef(false);
  const submitting = useRef(false);

  useEffect(() => {
    let cancelled = false;
    async function initialize() {
      if (!/^[A-Za-z0-9_-]{43}$/.test(invite || '')) {
        setError('Anket bağlantısı geçersiz.');
        setStatus('error');
        return;
      }
      try {
        let saved = readStored(invite);
        // On refresh, resume first; closed polls need not expose the public invitation.
        if (saved?.participant_token && saved?.session_id && saved?.poll) {
          try {
            const state = await callApi('/poll-sessions/' + saved.session_id + '/me', {
              headers: { Authorization: 'Bearer ' + saved.participant_token },
            });
            if (!cancelled) {
              setPoll(saved.poll);
              setParticipant(saved);
              setReceipt(state.vote);
              setStatus(state.status);
            }
            return;
          } catch (reason) {
            // A bad credential is not permission to silently mint a fresh identity.
            if (!cancelled) { setError(messageFor(reason)); setStatus('error'); }
            return;
          }
        }
        const publicPoll = await callApi('/poll-invites/' + invite);
        if (cancelled) return;
        setPoll(publicPoll);
        // The idempotency key must exist before the first HTTP join call.
        if (!saved?.join_key) {
          saved = { join_key: makeJoinKey() };
          saveStored(invite, saved);
        }
        if (joining.current) return;
        joining.current = true;
        const joined = await callApi('/poll-invites/' + invite + '/join', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ join_key: saved.join_key }),
        });
        const record = { ...saved, ...joined, poll: publicPoll };
        saveStored(invite, record);
        const state = await callApi('/poll-sessions/' + record.session_id + '/me', {
          headers: { Authorization: 'Bearer ' + record.participant_token },
        });
        if (!cancelled) {
          setParticipant(record);
          setReceipt(state.vote);
          setStatus(state.status);
        }
      } catch (reason) {
        if (!cancelled) { setError(messageFor(reason)); setStatus('error'); }
      } finally {
        joining.current = false;
      }
    }
    initialize();
    return () => { cancelled = true; };
  }, [invite]);

  async function vote() {
    if (!participant || receipt || selected === null || submitting.current || status !== 'open') return;
    submitting.current = true;
    setError('');
    try {
      const savedReceipt = await callApi('/poll-sessions/' + participant.session_id + '/votes', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer ' + participant.participant_token,
        },
        body: JSON.stringify({ option_index: selected }),
      });
      setReceipt(savedReceipt);
    } catch (reason) {
      // Timeout/409 might mean server accepted a vote. Ask the source of truth.
      try {
        const state = await callApi('/poll-sessions/' + participant.session_id + '/me', {
          headers: { Authorization: 'Bearer ' + participant.participant_token },
        });
        setReceipt(state.vote);
        setStatus(state.status);
        if (!state.vote) setError(messageFor(reason));
      } catch { setError(messageFor(reason)); }
    } finally {
      submitting.current = false;
    }
  }

  return <main className="qb-poll-page">
    <section className="qb-poll-card">
      <header className="qb-poll-brand">QuizBlast · Anket</header>
      {status === 'loading' && <p role="status">Ankete bağlanılıyor…</p>}
      {poll && status !== 'error' && <>
        <h1>{poll.question}</h1>
        {receipt
          ? <div role="status" className="qb-poll-confirmation">
              <strong>Oyunuz kaydedildi.</strong>
              <p>Seçiminiz: {poll.options[receipt.option_index]}</p>
              <small>Bu oy tekrar sayılmaz ve değiştirilemez.</small>
            </div>
          : status === 'closed'
            ? <p role="status">Anket kapandı. Yeni oy kabul edilmiyor.</p>
            : <div className="qb-poll-options" role="radiogroup" aria-label="Anket seçenekleri">
                {poll.options.map((option, index) => <label key={index} className="qb-poll-choice">
                  <input type="radio" name="poll-option" checked={selected === index}
                    onChange={() => setSelected(index)} disabled={status !== 'open'} />
                  <span>{option}</span>
                </label>)}
              </div>}
        {!receipt && status === 'open' && <button className="qb-poll-submit"
          type="button" disabled={selected === null || submitting.current}
          onClick={vote}>{submitting.current ? 'Gönderiliyor…' : 'Oyumu gönder'}</button>}
      </>}
      {error && <p className="qb-poll-error" role="alert">{error}</p>}
    </section>
  </main>;
}
function makeJoinKey() {
  const bytes = new Uint8Array(32);
  if (!window.crypto?.getRandomValues) throw new Error('secure_random_unavailable');
  window.crypto.getRandomValues(bytes);
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}
