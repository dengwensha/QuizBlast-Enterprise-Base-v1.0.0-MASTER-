import React, { useEffect, useState } from "react";
import { fetchContentSets, fetchContentSetPreview } from "../../services/contentService";
import "./content-library.css";

const COLLECTIONS = [
  { id: "education", name: "Eğitim Quizleri", icon: "🎓", description: "İlkokul ve ortaokul dersleri, sınıf ve konu bazlı quizler." },
  { id: "general_event", name: "Genel & Etkinlik Quizleri", icon: "🎉", description: "Genel kültür, bilim, eğlence ve takım etkinlikleri." },
];

// Older published sets predate the collection field and belong to general events.
const collectionOf = set => set.collection || "general_event";

export default function ContentLibrary({ onBack, onPlay, onCopy }) {
  const [sets, setSets] = useState([]);
  const [collection, setCollection] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");

  const loadSets = async () => {
    setLoading(true);
    setError("");
    try {
      const result = await fetchContentSets();
      if (!Array.isArray(result)) throw new Error("Katalog yanıtı geçersiz.");
      setSets(result);
    } catch (err) {
      setError(err.message || "Hazır setler yüklenemedi.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadSets(); }, []);

  const selectSet = async (setId) => {
    setSelectedId(setId);
    setPreview(null);
    setFeedback("");
    setPreviewLoading(true);
    try {
      const result = await fetchContentSetPreview(setId);
      setPreview(current => (current === null ? result : current));
    } catch (err) {
      setFeedback(err.message || "Önizleme yüklenemedi.");
    } finally {
      setPreviewLoading(false);
    }
  };

  const perform = async (fn) => {
    setBusy(true);
    setFeedback("");
    try {
      await fn();
    } catch (err) {
      setFeedback(err.message || "İşlem başarısız.");
    } finally {
      setBusy(false);
    }
  };

  const visibleSets = sets.filter(set => collectionOf(set) === collection);
  const displayMinutes = (seconds) => Math.max(1, Math.ceil((seconds || 0) / 60));

  return (
    <main className="qb-library">
      <div className="qb-library__shell">
        <header className="qb-library__header">
          <div>
            <span className="qb-library__eyebrow">QUIZBLAST</span>
            <h1>Hazır Quizler</h1>
            <p>Setleri keşfet, soruları incele, hemen oyna veya kendi quizlerine kopyala.</p>
          </div>
          <button type="button" className="qb-library__back" onClick={onBack}><span aria-hidden="true">⌂</span> Ana Menü</button>
        </header>
        {selectedId === null && collection === null && (
          <div className="qb-library__category-grid" aria-label="Quiz kategorileri">
            {COLLECTIONS.map(item => (
              <button type="button" key={item.id} className="qb-library__category" onClick={() => setCollection(item.id)}>
                <span aria-hidden="true" className="qb-library__category-icon">{item.icon}</span>
                <span className="qb-library__category-title">{item.name}</span>
                <span className="qb-library__category-description">{item.description}</span>
                <span className="qb-library__category-count">{sets.filter(set => collectionOf(set) === item.id).length} hazır quiz →</span>
              </button>
            ))}
          </div>
        )}
        {selectedId === null && collection !== null && (
          <div className="qb-library__category-heading">
            <button type="button" className="qb-library__back" onClick={() => setCollection(null)}>← Kategoriler</button>
            <h2>{COLLECTIONS.find(item => item.id === collection)?.name}</h2>
          </div>
        )}
        {error && <div role="alert" className="qb-library__alert">{error} <button onClick={loadSets}>Tekrar Dene</button></div>}
        {loading && <p role="status">Hazır setler yükleniyor...</p>}
        {!loading && !error && collection !== null && selectedId === null && visibleSets.length === 0 && (
          <div className="qb-library__empty">
            <div className="qb-library__empty-art" aria-hidden="true"><span className="qb-library__empty-card qb-library__empty-card--rear" /><span className="qb-library__empty-card qb-library__empty-card--middle" /><span className="qb-library__empty-card qb-library__empty-card--front">?</span></div>
            <h2>Bu kategoride henüz hazır quiz yok</h2>
            <p>Yeni içerikler yayınlandığında burada görünecek.</p>
          </div>
        )}
        {!loading && !error && selectedId === null && collection !== null && visibleSets.length > 0 && (
          <div className="qb-library__grid">
            {visibleSets.map(set => <article className="qb-library__card" key={set.id}>
              <span className="qb-library__topic">{set.topic}</span>
              <h2>{set.title}</h2>
              <p>{set.description}</p>
              <div className="qb-library__metadata">
                <span>{set.audience}</span><span>{set.difficulty}</span>
                <span>{set.question_count} soru</span><span>≈ {displayMinutes(set.estimated_duration_seconds)} dk</span>
              </div>
              <button type="button" className="qb-library__primary" onClick={() => selectSet(set.id)}>Seti İncele</button>
            </article>)}
          </div>
        )}
        {selectedId !== null && !loading && <section className="qb-library__details">
          <button type="button" className="qb-library__back" onClick={() => {setSelectedId(null);setPreview(null);setFeedback("");}}>← Bu Kategorideki Setler</button>
          {previewLoading && <p role="status">Sorular yükleniyor...</p>}
          {preview && !previewLoading && <>
            <h2>{preview.title}</h2>
            <p>{preview.description}</p>
            <div className="qb-library__metadata">
              <span>{preview.topic}</span><span>{preview.audience}</span><span>{preview.difficulty}</span>
              <span>{preview.question_count} soru</span><span>≈ {displayMinutes(preview.estimated_duration_seconds)} dk</span>
            </div>
            <div className="qb-library__actions">
              <button type="button" className="qb-library__primary" disabled={busy} onClick={() => perform(() => onPlay(preview))}>Doğrudan Oyna</button>
              <button type="button" className="qb-library__secondary" disabled={busy} onClick={() => perform(() => onCopy(preview))}>Kendi Quizlerime Kopyala</button>
            </div>
            <p className="qb-library__privacy">Orijinal set korunur. Düzenlemek için kendi quizlerine kopyala.</p>
            <h3>Soru Önizlemesi</h3>
            <ol className="qb-library__questions">
              {(preview.questions || []).map((q, index) =>
                <li key={index}><strong>{q.question}</strong>
                  {q.image_url && <img src={q.image_url} alt="Soru görseli" loading="lazy" />}
                  <ol type="A">{q.options.map((option, i) => <li key={i}>{option}</li>)}</ol>
                  <small>{q.time} saniye</small>
                </li>
              )}
            </ol>
          </>}
        </section>}
        {feedback && <p role="alert" className="qb-library__alert">{feedback}</p>}
      </div>
    </main>
  );
}
