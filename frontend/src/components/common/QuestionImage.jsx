import React, { useEffect, useState } from "react";
import { normalizeQuestionImage } from "../../utils/questionImage";

/** Optional image that never blocks answering when an external URL fails. */
export default function QuestionImage({ src, alt = "Soru görseli", className, style }) {
  const normalizedSrc = normalizeQuestionImage(src);
  const [failedSrc, setFailedSrc] = useState(null);
  useEffect(() => { setFailedSrc(null); }, [normalizedSrc]);

  if (!normalizedSrc) return null;
  if (failedSrc === normalizedSrc) {
    return <p role="status" className={className} style={{ ...style, maxHeight: "none" }}>
      Görsel yüklenemedi. Soruyu yanıtlamaya devam edebilirsiniz.
    </p>;
  }
  return <img src={normalizedSrc} alt={alt || "Soru görseli"} className={className}
    style={style} onError={() => setFailedSrc(normalizedSrc)} />;
}
