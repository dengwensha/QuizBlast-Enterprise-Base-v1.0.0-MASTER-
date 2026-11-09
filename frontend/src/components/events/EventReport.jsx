import React, { useEffect, useState } from 'react';
import { getEventReport } from '../../services/eventService';

export default function EventReport({ token, eventId, onBack }) {
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let current = true;
    getEventReport(token, eventId).then(data => {
      if (current) setReport(data);
    }).catch(e => {
      if (current) setError(e.message);
    });
    return () => { current = false; };
  }, [token, eventId]);
  const format = value => new Date(value).toLocaleString('tr-TR');
  return <main className="qb-events">
    <header><h1>Etkinlik Raporu</h1><button onClick={onBack}>Oturuma Dön</button></header>
    {error && <p role="alert">{error}</p>}
    {!report && !error && <p role="status">Rapor yükleniyor…</p>}
    {report && <section className="qb-events__panel">
      <h2>{report.event_title}</h2>
      <p>Quiz: {report.quiz_title}</p>
      <p>Tamamlanma: {format(report.completed_at)}</p>
      <p>Erişim bitişi: {format(report.expires_at)}</p>
      <p>Katılımcı sayısı: {report.ranking.length}</p>
      <table>
        <caption>Final sıralaması</caption>
        <thead><tr><th scope="col">Sıra</th><th scope="col">Oyuncu</th><th scope="col">Puan</th></tr></thead>
        <tbody>{report.ranking.map(({ name, score }, index) =>
          <tr key={name}><td>{index + 1}</td><td>{name}</td><td>{score}</td></tr>)}</tbody>
      </table>
    </section>}
  </main>;
}
