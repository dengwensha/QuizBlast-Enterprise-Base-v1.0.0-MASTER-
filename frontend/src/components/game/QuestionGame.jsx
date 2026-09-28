import React from "react";

import HostLiveStage from "./HostLiveStage";
import PlayerQuestionStage from "./PlayerQuestionStage";
import ResultReveal from "./ResultReveal";
import LeaderboardBoard from "./LeaderboardBoard";

export default function QuestionGame({ question, questionImage, timeLeft, answerCount, totalPlayers, mode, playerName, options, sendAnswer, answered, paused, questionResult, optionColors, visibleLeaderboard, nextQuestion, currentQuestionIndex, totalQuestions, styles }) {
  const safeOptions = Array.isArray(options) ? options : [];

  if (mode === "host") return <HostLiveStage {...{ question, questionImage, timeLeft, answerCount, totalPlayers, options: safeOptions, optionColors, questionResult, visibleLeaderboard, nextQuestion, currentQuestionIndex, totalQuestions, styles }} />;

  if (mode === "player" && playerName !== "DISPLAY") return <PlayerQuestionStage {...{ question, questionImage, timeLeft, answerCount, totalPlayers, options: safeOptions, sendAnswer, answered, paused, questionResult, optionColors, visibleLeaderboard, currentQuestionIndex, totalQuestions, styles }} />;

  return <>
    {paused && <p role="status">Host bekleniyor; oyun duraklatıldı.</p>}
    <div style={styles.questionCard}>
      <h1>{question}</h1>
      {questionImage && <img src={questionImage} alt="Soru görseli" style={styles.questionImage} />}
      <div data-testid="game-timer" style={styles.timerCircle}>{timeLeft}</div>
      <div style={styles.progressOuter}><div style={{ ...styles.progressInner, width: `${(timeLeft / 15) * 100}%` }} /></div>
      <h3>Cevaplayan: {answerCount} / {totalPlayers}</h3>
    </div>
    {questionResult && <ResultReveal questionResult={questionResult} options={safeOptions} optionColors={optionColors} styles={styles} />}
    <LeaderboardBoard visibleLeaderboard={visibleLeaderboard} styles={styles} />
  </>;
}
