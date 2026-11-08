import { API } from './api';

async function request(token, path = '', options = {}) {
  const response = await fetch(`${API}/events${path}`, {
    ...options,
    headers: { Authorization: `Bearer ${token}`, ...(options.body ? { 'Content-Type': 'application/json' } : {}) },
  });
  const data = await response.json();
  if (!response.ok) {
    const messages = {
      401: 'Oturumunuz sona erdi. Yeniden giriş yapın.',
      404: 'Etkinlik bulunamadı veya erişiminiz yok.',
      409: 'Etkinlik başka bir yerde güncellendi. Güncel kaydı yeniden açın.',
      422: 'Başlık ve tarih bilgilerini kontrol edin.',
    };
    const details = {
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
