export default function QuestionList({
  title,
  questions,
  onDelete,
  onEdit,
  showDelete = false,
  styles,
}) {
  return (
    <div style={styles.card}>
      <h2>{title}</h2>

      {questions.length === 0 && <p>Bu quizde henüz soru yok.</p>}

      {questions.map((q, i) => (
        <div key={q.id} style={styles.questionDetailCard}>
          <div>
            <h3>
              {i + 1}. {q.question}
            </h3>

            {q.image_url && (
              <img
                src={q.image_url}
                alt="Soru görseli"
                style={styles.previewImage}
              />
            )}

            <ol>
              {q.options?.map((opt, index) => (
                <li
                  key={index}
                  style={{
                    fontWeight: q.correct === index ? "bold" : "normal",
                    color: q.correct === index ? "green" : "black",
                    marginBottom: 6,
                  }}
                >
                  {opt} {q.correct === index ? "✅" : ""}
                </li>
              ))}
            </ol>

            <p>
              <b>Süre:</b> {q.time} saniye
            </p>
          </div>

          {showDelete && (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button
                onClick={() => onEdit && onEdit(q)}
                style={{
                  ...styles.purpleButton,
                  padding: "8px 12px",
                  fontSize: 14,
                }}
              >
                Düzelt
              </button>

              <button
                onClick={() => onDelete(q.id)}
                style={styles.deleteButton}
              >
                Sil
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}