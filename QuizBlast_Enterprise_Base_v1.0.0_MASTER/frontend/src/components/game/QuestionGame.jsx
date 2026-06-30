import HostLiveStage from "./HostLiveStage";
import ResultReveal from "./ResultReveal";
import LeaderboardBoard from "./LeaderboardBoard";

export default function QuestionGame({
  question,
  questionImage,
  timeLeft,
  answerCount,
  totalPlayers,
  mode,
  playerName,
  options,
  sendAnswer,
  answered,
  questionResult,
  optionColors,
  visibleLeaderboard,
  nextQuestion,
  currentQuestionIndex,
  totalQuestions,
  styles,
}) {
  const safeOptions = Array.isArray(options) ? options : [];

  if (mode === "host") {
    return (
      <HostLiveStage
        question={question}
        questionImage={questionImage}
        timeLeft={timeLeft}
        answerCount={answerCount}
        totalPlayers={totalPlayers}
        options={safeOptions}
        optionColors={optionColors}
        questionResult={questionResult}
        visibleLeaderboard={visibleLeaderboard}
        nextQuestion={nextQuestion}
        currentQuestionIndex={currentQuestionIndex}
        totalQuestions={totalQuestions}
        styles={styles}
      />
    );
  }

  return (
    <>
      <div style={styles.questionCard}>
        <h1>{question}</h1>

        {questionImage && (
          <img src={questionImage} alt="Soru görseli" style={styles.questionImage} />
        )}

        <div style={styles.timerCircle}>{timeLeft}</div>

        <div style={styles.progressOuter}>
          <div
            style={{
              ...styles.progressInner,
              width: `${(timeLeft / 15) * 100}%`,
            }}
          />
        </div>

        <h3>Cevaplayan: {answerCount} / {totalPlayers}</h3>
      </div>

      {mode === "player" && playerName !== "DISPLAY" && (
        <div style={styles.answers}>
          {safeOptions.map((opt, i) => (
            <button
              key={i}
              onClick={() => sendAnswer(i)}
              disabled={answered || timeLeft <= 0}
              style={{
                ...styles.answerButton,
                background: optionColors[i],
                opacity: answered || timeLeft <= 0 ? 0.6 : 1,
              }}
            >
              {opt}
            </button>
          ))}
        </div>
      )}

      {answered && <div style={styles.answered}>✅ Cevabın alındı</div>}

      {questionResult && (
        <ResultReveal
          questionResult={questionResult}
          options={safeOptions}
          optionColors={optionColors}
          styles={styles}
        />
      )}

      <LeaderboardBoard visibleLeaderboard={visibleLeaderboard} styles={styles} />
    </>
  );
}