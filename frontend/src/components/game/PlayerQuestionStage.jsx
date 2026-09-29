import React from "react";

import { Alert, Button, Card } from "../ui";
import PlayerResultReveal from "./PlayerResultReveal";
import LeaderboardBoard from "./LeaderboardBoard";
import "./player-question-stage.css";

export default function PlayerQuestionStage({ question, questionImage, timeLeft, answerCount, totalPlayers, options, sendAnswer, answered, paused, questionResult, optionColors, visibleLeaderboard, currentQuestionIndex, totalQuestions, styles }) {
  const disabled = answered || paused || timeLeft <= 0;
  const progress = Math.max(0, Math.min(100, (timeLeft / 15) * 100));

  return <section className="qb-player-question" aria-label="Quiz question">
    {paused && <div role="status" className="qb-player-question__pause-status">Host bekleniyor; oyun duraklatıldı.</div>}
    <Card className="qb-player-question__card">
      <div className="qb-player-question__meta"><span>{totalQuestions ? `Soru ${currentQuestionIndex + 1} / ${totalQuestions}` : "Soru"}</span><span>Cevaplayan: {answerCount} / {totalPlayers}</span></div>
      <h1 className="qb-player-question__title">{question}</h1>
      {questionImage && <img className="qb-player-question__image" src={questionImage} alt="Soru görseli" />}
      <div className="qb-player-question__timer" data-testid="game-timer" aria-label={`Kalan süre ${timeLeft} saniye`}>{timeLeft}</div>
      <div className="qb-player-question__progress" aria-hidden="true"><div className="qb-player-question__progress-value" style={{ width: `${progress}%` }} /></div>
    </Card>
    <div className="qb-player-question__answers" aria-label="Cevap seçenekleri">
      {options.map((option, index) => <Button key={index} type="button" className={`qb-answer qb-answer--${index + 1}`} disabled={disabled} onClick={() => sendAnswer(index)} style={{ "--qb-answer-fallback": optionColors[index] }}>{option}</Button>)}
    </div>
    {answered && !questionResult && <Alert variant="success" role="note" title="✅ Cevabın alındı">Diğer oyuncular bekleniyor.</Alert>}
    {questionResult && <PlayerResultReveal questionResult={questionResult} options={options} optionColors={optionColors} />}
    <LeaderboardBoard visibleLeaderboard={visibleLeaderboard} styles={styles} />
  </section>;
}
