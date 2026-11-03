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
    throw new Error(messages[response.status] || 'Etkinlik işlemi tamamlanamadı. Tekrar deneyin.');
  }
  return data;
}

export const listEvents = (token, offset = 0) => request(token, `?limit=20&offset=${offset}`);
export const getEvent = (token, id) => request(token, `/${id}`);
export const saveEvent = (token, id, data) => request(token, id ? `/${id}` : '', {
  method: id ? 'PATCH' : 'POST', body: JSON.stringify(data),
});
