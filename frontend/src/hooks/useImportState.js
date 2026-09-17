import { useState } from "react";
import {
  previewImportRequest,
  commitImportRequest
} from "../services/importService";

function useImportState({ user, selectedQuizId, onImportCommitted }) {
  const [importPreview, setImportPreview] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importSummary, setImportSummary] = useState(null);

  const importExcel = async (e) => {
    if (!selectedQuizId) return alert("Quiz seç");

    const file = e.target.files[0];
    if (!file) return;

    try {
      setImportSummary(null);
      setImportPreview(null);

      const d = await previewImportRequest(user, selectedQuizId, file);

      if (d.error) {
        alert(d.message || d.error);
        e.target.value = "";
        return;
      }

      setImportPreview(d);

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
      e.target.value = "";
    } catch (err) {
      console.error(err);
      alert(
        "Excel ön izleme sırasında hata oluştu. Backend preview endpoint çalışıyor mu kontrol et."
      );
      e.target.value = "";
    }
  };

  const commitImport = async () => {
    if (!selectedQuizId) return alert("Quiz seç");
    if (!importPreview) return alert("Önce Excel ön izleme yap.");

    const items = importPreview.importable_payloads || [];

    if (items.length === 0) {
      return alert("Import edilebilir soru yok.");
    }

    if (!confirm(`${items.length} soru veritabanına aktarılsın mı?`)) {
      return;
    }

    try {
      setImporting(true);

      const d = await commitImportRequest(user, selectedQuizId, {
        session_id: importPreview.session_id,
        filename: importPreview.filename,
        duplicate_policy: "skip",
        overwrite: false,
        items
      });

      setImportSummary(d);

      if (d.error) {
        alert(d.message || d.error);
        return;
      }

      alert(
        `Import tamamlandı.\nAktarılan: ${d.imported}\nAtlanan: ${d.skipped}\nSession: ${d.session_id}`
      );

      setImportPreview(null);
      await onImportCommitted(selectedQuizId);
    } catch (err) {
      console.error(err);
      alert("Import commit sırasında hata oluştu.");
    } finally {
      setImporting(false);
    }
  };

  return {
    importPreview,
    importing,
    importSummary,
    importExcel,
    commitImport
  };
}

export { useImportState };