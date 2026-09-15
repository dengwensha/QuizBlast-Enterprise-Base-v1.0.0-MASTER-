import QuestionList from "../question/QuestionList";

export default function HostSetup({
  setMode,
  selectedQuizId,
  setSelectedQuizId,
  loadSelectedQuestions,
  quizzes,
  finalLimit,
  setFinalLimit,
  createRoom,
  selectedQuestions,
  styles,
}) {
  return (
    <div style={styles.app}>
      <div style={styles.topbar}>
        <h1>Host Dashboard 🚀</h1>

        <button
          onClick={() => setMode(null)}
          style={styles.hostButton}
        >
          Ana Menü
        </button>
      </div>

      <div style={styles.container}>
        <div style={styles.card}>
          <h2>Quiz Seç</h2>

          <select
            value={selectedQuizId}
            onChange={(e) => {
              setSelectedQuizId(e.target.value);
              loadSelectedQuestions(e.target.value);
            }}
            style={styles.input}
          >
            <option value="">Quiz seç</option>

            {quizzes.map((q) => (
              <option key={q.id} value={String(q.id)}>
                {q.title} ({q.questions?.length || 0} soru)
              </option>
            ))}
          </select>

          <label>
            Final sıralamada gösterilecek kişi sayısı
          </label>

          <input
            type="number"
            min="3"
            max="10"
            value={finalLimit}
            onChange={(e) =>
              setFinalLimit(
                Math.min(
                  Math.max(Number(e.target.value), 3),
                  10
                )
              )
            }
            style={styles.input}
          />

          <button
            onClick={createRoom}
            style={styles.purpleButton}
          >
            Create Room
          </button>
        </div>

        <QuestionList
          title="Host Quiz Önizleme"
          questions={selectedQuestions}
          styles={styles}
        />
      </div>
    </div>
  );
}