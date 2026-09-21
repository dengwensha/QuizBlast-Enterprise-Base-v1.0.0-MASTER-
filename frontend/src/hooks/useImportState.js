import { useLayoutEffect, useRef, useState } from "react";
import {
  previewImportRequest,
  commitImportRequest
} from "../services/importService";

function useImportState({ user, selectedQuizId, onImportCommitted }) {
  const [importPreview, setImportPreview] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importSummary, setImportSummary] = useState(null);

  const contextRef = useRef(null);
  const email = user?.email;
  const token = user?.token;
  const quizId = String(selectedQuizId || "");

  // Each committed context gets a new identity, including A -> B -> A.
  // Layout cleanup invalidates requests before the next user interaction.
  useLayoutEffect(() => {
    const context = { email, token, quizId, previewRequest: 0, preview: null, committing: false };
    contextRef.current = context;
    setImportPreview(null);
    setImportSummary(null);
    setImporting(false);
    return () => {
      if (contextRef.current === context) contextRef.current = null;
    };
  }, [email, token, quizId]);

  const currentContext = () => {
    const context = contextRef.current;
    return context && context.email === email && context.token === token &&
      context.quizId === quizId ? context : null;
  };

  const importExcel = async (e) => {
    if (!selectedQuizId) return alert("Quiz seç");

    const input = e.target;
    const file = input.files[0];
    input.value = "";
    if (!file) return;
    const context = currentContext();
    if (!context || !token || context.committing) return;
    context.preview = null;
    const request = ++context.previewRequest;
    const isCurrent = () => contextRef.current === context &&
      context.previewRequest === request;

    try {
      setImportSummary(null);
      setImportPreview(null);

      const d = await previewImportRequest(user, context.quizId, file);
      if (!isCurrent()) return;
      if (d.error) {
        alert(d.message || d.error);
        return;
      }
      if (String(d.quiz_id) !== context.quizId) {
        alert("Önizleme quiz bilgisi eşleşmiyor. Dosyayı yeniden seç.");
        return;
      }

      const preview = { data: d, context };
      context.preview = preview;
      setImportPreview(preview);

      const summary = d.preview_payload?.summary || {};
      const issues = d.preview_payload?.issues || [];
      const mappingErrors = d.mapping_errors || [];

      let message = "Excel ön izleme tamamlandı.\n\n";
      message += `Dosya: ${d.filename || file.name}\n`;
      message += `Session: ${d.session_id || "-"}\n`;
      message += `Toplam satır: ${summary.total_rows ?? 0}\n`;
      message += `Önizleme satırı: ${summary.preview_rows ?? 0}\n`;
      message += `Import edilebilir: ${summary.importable_rows ?? 0}\n`;
      message += `Bloklanan: ${summary.blocked_rows ?? 0}\n`;
      message += `Hata: ${summary.error_count ?? 0}\n`;
      message += `Uyarı: ${summary.warning_count ?? 0}\n`;

      if (mappingErrors.length > 0) {
        message += "\nMapping hataları:\n";

        mappingErrors.slice(0, 8).forEach((err) => {
          message += `Satır ${err.row_no}: ${err.message}\n`;
        });

        if (mappingErrors.length > 8) {
          message += `... ${mappingErrors.length - 8} hata daha\n`;
        }
      }

      if (issues.length > 0) {
        message += "\nValidation detayları:\n";

        issues.slice(0, 10).forEach((issue) => {
          message += `Satır ${issue.row_no} | ${issue.severity} | ${issue.code}: ${issue.message}\n`;
        });

        if (issues.length > 10) {
          message += `... ${issues.length - 10} detay daha\n`;
        }
      }

      message +=
        "\nUygunsa ekrandaki Import Et butonu ile veritabanına aktarabilirsin.";

      alert(message);
      console.log("QBDS Preview Result", d);
    } catch (err) {
      if (!isCurrent()) return;
      console.error(err);
      alert(
        "Excel ön izleme sırasında hata oluştu. Backend preview endpoint çalışıyor mu kontrol et."
      );
    }
  };

  const commitImport = async () => {
    if (!selectedQuizId) return alert("Quiz seç");
    const context = currentContext();
    if (!context || !token || context.committing) return;
    if (!importPreview || importPreview.context !== context ||
        context.preview !== importPreview) {
      return alert("Önce Excel ön izleme yap.");
    }
    const preview = importPreview.data;
    if (String(preview.quiz_id) !== context.quizId) {
      setImportPreview(null);
      return alert("Quiz değişti. Excel ön izlemesini yeniden yap.");
    }
    const isCurrent = () => contextRef.current === context;
    const items = preview.importable_payloads || [];

    if (items.length === 0) {
      return alert("Import edilebilir soru yok.");
    }

    if (!confirm(`${items.length} soru veritabanına aktarılsın mı?`)) {
      return;
    }

    if (!isCurrent()) return;
    context.committing = true;
    ++context.previewRequest;
    try {
      setImporting(true);

      const d = await commitImportRequest(user, context.quizId, {
        session_id: preview.session_id,
        filename: preview.filename,
        duplicate_policy: "skip",
        overwrite: false,
        items
      });

      if (!isCurrent()) return;
      setImportSummary(d);

      if (d.error) {
        alert(d.message || d.error);
        return;
      }

      alert(
        `Import tamamlandı.\nAktarılan: ${d.imported}\nAtlanan: ${d.skipped}\nSession: ${d.session_id}`
      );

      context.preview = null;
      setImportPreview(null);
      await onImportCommitted(context.quizId);
    } catch (err) {
      if (!isCurrent()) return;
      console.error(err);
      alert("Import commit sırasında hata oluştu.");
    } finally {
      context.committing = false;
      if (isCurrent()) setImporting(false);
    }
  };

  return {
    importPreview: importPreview?.data || null,
    importing,
    importSummary,
    importExcel,
    commitImport
  };
}

export { useImportState };
