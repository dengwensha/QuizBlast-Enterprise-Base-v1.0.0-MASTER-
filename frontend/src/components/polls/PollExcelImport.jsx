import React, { useRef, useState } from 'react';
import { API } from '../../services/api';

const labels = {
  poll_import_cell_invalid: 'Hücrede formül veya geçersiz veri tipi var.',
  poll_import_poll_invalid: 'Soru veya seçenekler geçersiz (2–6 farklı seçenek gerekli).',
  poll_import_xlsx_required: 'Yalnızca .xlsx dosyası yükleyebilirsiniz.',
  poll_import_file_too_large: 'Dosya 1 MB sınırını aşıyor.',
  poll_import_header_invalid: 'Sütun başlıkları şablona uygun değil.',
  poll_import_row_limit: 'En fazla 100 anket satırı yükleyebilirsiniz.',
  poll_import_xlsx_invalid: 'Excel dosyası okunamadı.',
  poll_import_validation_failed: 'Dosya kaydetme öncesinde yeniden doğrulandı ve hatalar bulundu.',
};

async function upload(file, token, action) {
  const body = new FormData();
  body.append('file', file);
  const response = await fetch(API + '/polls/import/' + action, {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + token },
    body,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(typeof data.detail === 'string'
      ? data.detail : data.detail?.code || 'import_failed');
    error.rows = data.detail?.errors || [];
    throw error;
  }
  return data;
}

export default function PollExcelImport({ token, onImported }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(0);
  const picker = useRef(null);
  const inFlight = useRef(false);

  function choose(event) {
    if (inFlight.current) return;
    setFile(event.target.files?.[0] || null);
    setPreview(null);
    setError('');
    setSaved(0);
  }

  async function perform(action) {
    if (!file || !token || inFlight.current || (action === 'commit' && !preview?.can_commit)) return;
    inFlight.current = true;
    setBusy(true);
    setError('');
    try {
      const data = await upload(file, token, action);
      if (action === 'preview') setPreview(data);
      else {
        setSaved(data.imported_count);
        setPreview(null);
        setFile(null);
        if (picker.current) picker.current.value = '';
        await onImported?.();
      }
    } catch (reason) {
      setError(labels[reason.message] || 'Excel işlemi tamamlanamadı.');
      if (action === 'commit') {
        setPreview(previous => previous
          ? { ...previous, can_commit: false, errors: reason.rows.length ? reason.rows : previous.errors }
          : null);
      }
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }

  return <section className="qb-poll-host__excel" aria-label="Excel anket içe aktarma">
    <h3>Excel'den anket yükle</h3>
    <p>İlk çalışma sayfası; Soru, Seçenek1–Seçenek6 sütunları. En fazla 100 anket, 1 MB.</p>
    <label>Excel dosyası
      <input ref={picker} type="file" accept=".xlsx" onChange={choose} disabled={busy} />
    </label>
    <button type="button" disabled={!file || busy} onClick={() => perform('preview')}>
      {busy ? 'İşleniyor…' : 'Dosyayı önizle'}
    </button>
    {error && <p role="alert" className="qb-poll-host__error">{error}</p>}
    {preview && <div aria-label="Excel önizleme sonucu">
      <p role="status">{preview.count} geçerli anket · {preview.error_count} hatalı satır</p>
      {preview.errors.length > 0 && <ul>{preview.errors.map(item =>
        <li key={item.row}>Satır {item.row}: {labels[item.code] || item.code}</li>)}</ul>}
      <ol>{preview.items.map(item =>
        <li key={item.row}><strong>{item.question}</strong>
          <span> ({item.options.join(' / ')})</span>
        </li>)}</ol>
      <button type="button" disabled={!preview.can_commit || busy}
        onClick={() => perform('commit')}>Doğrulanan {preview.count} anketi toplu kaydet</button>
      {!preview.can_commit && <p>Hatalar düzeltilmeden hiçbir anket kaydedilemez.</p>}
    </div>}
    {saved > 0 && <p role="status">{saved} anket başarıyla kaydedildi. Hazır anket listesinden seçebilirsiniz.</p>}
  </section>;
}
