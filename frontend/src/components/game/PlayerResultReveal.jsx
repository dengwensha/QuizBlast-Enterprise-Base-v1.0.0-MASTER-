import React from "react";

import { Card } from "../ui";
import "./player-result-reveal.css";

export default function PlayerResultReveal({ questionResult, options = [], optionColors = [] }) {
  const correctIndex = questionResult?.correct;
  const correctText = options[correctIndex];
  const stats = Array.isArray(questionResult?.stats) ? questionResult.stats : [];
  const maxCount = Math.max(...stats, 1);

  return (
    <Card className="qb-player-result" aria-label="Soru sonucu">
      <p className="qb-player-result__eyebrow">Soru sonucu</p>
      <h2 className="qb-player-result__title">Doğru Cevap</h2>
      <div className="qb-player-result__correct" style={{ "--qb-result-color": optionColors[correctIndex] || "var(--qb-primary-600)" }}>
        {correctText}
      </div>
      {questionResult?.explanation && <p><strong>Açıklama:</strong> {questionResult.explanation}</p>}
      <h3 className="qb-player-result__distribution-title">Cevap Dağılımı</h3>
      <div className="qb-player-result__distribution">
        {stats.map((count, index) => {
          const width = `${(count / maxCount) * 100}%`;
          return (
            <div className="qb-player-result__row" key={index}>
              <div className="qb-player-result__label">
                <span><strong>{String.fromCharCode(65 + index)})</strong> {options[index]}</span>
                <span>{count} kişi</span>
              </div>
              <div className="qb-player-result__bar" aria-hidden="true">
                <div className="qb-player-result__bar-value" style={{ width, "--qb-result-color": optionColors[index] || "var(--qb-primary-600)" }} />
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
