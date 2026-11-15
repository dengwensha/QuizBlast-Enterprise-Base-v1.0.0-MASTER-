import { API } from './api';

async function request(token, path = '', options = {}) {
  const response = await fetch(`${API}/events${path}`, {
    ...options,
    headers: { Authorization: `Bearer ${token}`, ...(typeof options.body === 'string' ? { 'Content-Type': 'application/json' } : {}) },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const messages = {
      401: 'Oturumunuz sona erdi. Yeniden giriş yapın.',
      404: 'Etkinlik bulunamadı veya erişiminiz yok.',
      413: 'PDF dosyası yükleme sınırını aşıyor.',
      409: 'Etkinlik başka bir yerde güncellendi. Güncel kaydı yeniden açın.',
      422: 'Başlık ve tarih bilgilerini kontrol edin.',
    };
    const details = {
      event_pdf_invalid: 'PDF açılamadı veya dosya 10 MB, 30 sayfa ya da görsel boyutu sınırını aşıyor.',
      event_deck_limit: 'Etkinlik başına en fazla 12 PDF yüklenebilir.',
      event_deck_invalid: 'Seçilen PDF bu sunum adımına bağlanamadı.',
      event_agenda_required: 'Önce etkinlik programını kaydet.',
      event_quiz_not_completed: 'Sonraki adıma geçmeden quizi tamamla.',
      event_run_transition_invalid: 'Bu işlem programın mevcut adımında kullanılamıyor.',
      event_report_unavailable: 'Bu oturum için final raporu bulunamadı.',
      event_report_expired: 'Raporun erişim süresi doldu.',
      event_session_locked: 'Oturum oluşturulduktan sonra quiz değiştirilemez.',
      event_quiz_required: 'Önce bir quiz seçip kaydedin.',
      no_questions: 'Seçilen quizde soru bulunmuyor.',
      quiz_not_found: 'Quiz bulunamadı veya erişiminiz yok.',
    };
    throw new Error(details[data.detail] || messages[response.status] || 'Etkinlik işlemi tamamlanamadı. Tekrar deneyin.');
  }
  return data;
}

export const listEvents = (token, offset = 0) => request(token, `?limit=20&offset=${offset}`);
export const getEvent = (token, id) => request(token, `/${id}`);
export const saveEvent = (token, id, data) => request(token, id ? `/${id}` : '', {
  method: id ? 'PATCH' : 'POST', body: JSON.stringify(data),
});

export const getEventGame = (token, id) => request(token, `/${id}/game`);
export const selectEventQuiz = (token, id, quiz_id, revision) => request(token, `/${id}/quiz`, {
  method: 'PUT', body: JSON.stringify({ quiz_id, revision }),
});
export const createEventSession = (token, id, revision) => request(token, `/${id}/session`, {
  method: 'POST', body: JSON.stringify({ revision }),
});

export const getEventReport = (token, id) => request(token, `/${id}/report`);

export const copyEvent = (token, id) => request(token, `/${id}/copy`, { method: 'POST' });

export const getEventAgenda = (token, id) => request(token, `/${id}/agenda`);
export const saveEventAgenda = (token, id, data) => request(token, `/${id}/agenda`, {
  method: 'PUT', body: JSON.stringify(data),
});

export const getEventLive = (token, id) => request(token, `/${id}/live`);
export const startEventLive = (token, id) => request(token, `/${id}/live`, { method: 'POST' });
export const advanceEventLive = (token, id, data) => request(token, `/${id}/live`, {
  method: 'PUT', body: JSON.stringify(data),
});
export const getEventDisplay = token => request(token, '/display/program/state', { cache: 'no-store' });

export const uploadEventDeck = (token, id, file) => {
  const body = new FormData();
  body.append('file', file);
  return request(token, `/${id}/decks`, { method: 'POST', body });
};

export async function getSlideImage(token, path) {
  const response = await fetch(`${API}/events${path}`, {
    headers: { Authorization: `Bearer ${token}` }, cache: 'no-store',
  });
  if (!response.ok) throw new Error('Slayt yüklenemedi.');
  return { blob: await response.blob(), count: Number(response.headers.get('X-Page-Count')) };
}
