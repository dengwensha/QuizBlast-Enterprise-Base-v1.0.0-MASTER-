import React, { useEffect, useRef, useState } from "react";
import "./question-progress.css";

export default function QuestionProgress({ active, index, total, isSnapshot }) {
  const valid = Boolean(active) && Number.isInteger(index) && index >= 0;
  const seen = useRef(valid ? index : null);
  const [notice, setNotice] = useState(null);
  const number = index + 1;
  const hasTotal = Number.isInteger(total) && total > index;
  const position = hasTotal ? `${number} / ${total}` : `${number}`;

  useEffect(() => {
    if (!valid) {
      seen.current = null;
      setNotice(null);
      return;
    }
    if (seen.current === index) {
      if (isSnapshot) setNotice(null);
      return;
    }
    seen.current = index;
    setNotice(isSnapshot ? null : { index });
  }, [valid, index, isSnapshot]);

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(null), 3000);
    return () => window.clearTimeout(timer);
  }, [notice]);

  if (!valid) return null;

  return (
    <div className="qb-question-progress">
      <span className="qb-question-progress__badge" role="note" aria-label="Soru ilerlemesi">
        Soru {position}
      </span>
      {notice?.index === index && (
        <div key={notice.index} className="qb-question-progress__notice" role="status" aria-label="Yeni soru" aria-live="polite">
          <span>Yeni soru</span>
          <strong>{position}</strong>
        </div>
      )}
    </div>
  );
}
