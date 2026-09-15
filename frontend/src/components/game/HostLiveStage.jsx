import ResultReveal from "./ResultReveal";
import LeaderboardBoard from "./LeaderboardBoard";

export default function HostLiveStage({
  question,
  questionImage,
  timeLeft,
  answerCount,
  totalPlayers,
  options,
  optionColors,
  questionResult,
  visibleLeaderboard,
  nextQuestion,
  currentQuestionIndex,
  totalQuestions,
  styles,
}) {
  return (
    <div style={styles.liveStage}>
      <div style={styles.liveQuestionCard}>
        <div style={styles.liveQuestionText}>{question}</div>

        {questionImage && (
          <img
            src={questionImage}
            alt="Soru görseli"
            style={styles.liveQuestionImage}
          />
        )}

        <div
          style={{
            ...styles.liveTimer,
            background: timeLeft <= 5 ? "#e21b3c" : "#46178f",
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
                background: optionColors[i] || "#46178f",
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
              onClick={nextQuestion}
              style={styles.nextQuestionButton}
            >
              {currentQuestionIndex + 1 >= totalQuestions
                ? "🏁 Sonuçları Göster"
                : "➜ Sonraki Soru"}
            </button>
          </div>
        </>
      )}

      <LeaderboardBoard
        visibleLeaderboard={visibleLeaderboard}
        live
        styles={styles}
      />
    </div>
  );
}