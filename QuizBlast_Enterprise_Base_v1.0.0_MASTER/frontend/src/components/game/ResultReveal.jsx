export default function ResultReveal({
  questionResult,
  options,
  optionColors,
  live = false,
  styles,
}) {
  const correctIndex = questionResult.correct;
  const correctText = options[correctIndex];

  return (
    <div style={live ? styles.liveResultCard : styles.card}>
      <h2 style={live ? styles.liveResultTitle : undefined}>Doğru Cevap</h2>

      <div
        style={{
          ...(live ? styles.liveCorrectAnswer : styles.correctAnswer),
          background: optionColors[correctIndex] || "#46178f",
        }}
      >
        {correctText}
      </div>

      <h3>Cevap Dağılımı</h3>

      {questionResult.stats?.map((count, i) => {
        const maxCount = Math.max(...questionResult.stats, 1);
        const width = `${(count / maxCount) * 100}%`;

        return (
          <div key={i} style={styles.resultRow}>
            <div style={live ? styles.liveResultLabel : styles.resultLabel}>
              <b>{String.fromCharCode(65 + i)})</b> {options[i]} → {count} kişi
            </div>

            <div style={styles.resultBarOuter}>
              <div
                style={{
                  ...styles.resultBarInner,
                  width,
                  background: optionColors[i] || "#46178f",
                }}
              >
                {count}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}