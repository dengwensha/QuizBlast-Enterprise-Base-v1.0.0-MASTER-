import QuestionImage from "../common/QuestionImage";
import React from "react";

import ResultReveal from "./ResultReveal";

import LeaderboardBoard from "./LeaderboardBoard";
import "./host-live-stage.css";

export default function HostLiveStage({
  question,
  questionImage,
  timeLeft,
  answerCount,
  totalPlayers,
  options,
  optionColors,
  questionResult,
  gameStage,
  visibleLeaderboard,
  nextQuestion,
  revealLeaderboard,
  currentQuestionIndex,
  totalQuestions,
  styles,
}) {
  if (gameStage === "leaderboard") return <div style={styles.liveStage}><LeaderboardBoard visibleLeaderboard={visibleLeaderboard} live styles={styles} /><div style={{ textAlign: "center", marginTop: 20 }}><button onClick={nextQuestion} className="qb-host-live__next-action" style={styles.nextQuestionButton}>{currentQuestionIndex + 1 >= totalQuestions ? "🏁 Sonuçları Göster" : "➜ Sonraki Soru"}</button></div></div>;

  return (
    <div style={styles.liveStage}>
      <div style={styles.liveQuestionCard}>
        <div style={styles.liveQuestionText}>{question}</div>

        <QuestionImage src={questionImage} style={styles.liveQuestionImage} />

        <div
          data-testid="game-timer"
          style={{
            ...styles.liveTimer,
            background: timeLeft <= 5 ? "var(--qb-danger)" : "var(--qb-primary-600)",
            animation:
              timeLeft <= 5 ? "timerUrgent 0.8s infinite" : undefined,
          }}
        >
          {timeLeft}
        </div>

        <div style={styles.liveProgressOuter}>
          <div
            style={{
              ...styles.liveProgressInner,
              width: `${(timeLeft / 15) * 100}%`,
            }}
          />
        </div>

        <div style={styles.liveAnswerCount}>
          Cevaplayan: {answerCount} / {totalPlayers}
        </div>
      </div>

      {!questionResult && (
        <div style={styles.liveOptionsGrid}>
          {options.map((opt, i) => (
            <div
              key={i}
              style={{
                ...styles.liveOptionCard,
                background: optionColors[i] || "var(--qb-primary-600)",
                animationDelay: `${i * 0.35}s`,
              }}
            >
              <div style={styles.liveOptionLetter}>
                {String.fromCharCode(65 + i)}
              </div>

              <div style={styles.liveOptionText}>{opt}</div>
            </div>
          ))}
        </div>
      )}

      {questionResult && (
        <>
          <ResultReveal
            questionResult={questionResult}
            options={options}
            optionColors={optionColors}
            live
            styles={styles}
          />

          <div style={{ textAlign: "center", marginTop: 20 }}>
            <button
              onClick={revealLeaderboard}
              className="qb-host-live__next-action"
              style={styles.nextQuestionButton}
            >
              🏆 Sıralamayı Göster
            </button>
          </div>
        </>
      )}


    </div>
  );
}
