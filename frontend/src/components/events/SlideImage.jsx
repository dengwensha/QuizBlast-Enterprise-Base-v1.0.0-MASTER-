import React, { useEffect, useState } from 'react';
import { getSlideImage } from '../../services/eventService';

export default function SlideImage({ token, path, onCount }) {
  const [url, setUrl] = useState('');
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    let objectUrl;
    setUrl(''); setError('');
    getSlideImage(token, path).then(({ blob, count }) => {
      if (!active) return;
      objectUrl = URL.createObjectURL(blob);
      setUrl(objectUrl);
      if (count) onCount?.(count);
    }).catch(e => { if (active) setError(e.message); });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [token, path, onCount]);
  return error ? <p role="alert">{error}</p> : url
    ? <img src={url} alt="Sunum slaytı" style={{ display: 'block', maxWidth: '100%', maxHeight: '82vh', margin: 'auto' }} />
    : <p role="status">Slayt yükleniyor…</p>;
}
