export default function GameOver({
  podium,
  visibleLeaderboard,
  finalLimit,
  styles,
}) {
  return (
    <div style={styles.gameOver}>
      <h1 style={styles.gameOverTitle}>GAME OVER 🎉</h1>

      <div style={styles.podium}>
        {podium[1] && (
          <div
            style={{
              ...styles.podiumItem,
              ...styles.podiumSilver,
              height: 180,
              background: "#c0c0c0",
            }}
          >
            🥈
            <h2>{podium[1][0]}</h2>
            <h3>{podium[1][1]}</h3>
          </div>
        )}

        {podium[0] && (
          <div
            style={{
              ...styles.podiumItem,
              ...styles.podiumGold,
              height: 240,
              background: "#ffd700",
            }}
          >
            👑
            <h1>{podium[0][0]}</h1>
            <h2>{podium[0][1]}</h2>
          </div>
        )}

        {podium[2] && (
          <div
            style={{
              ...styles.podiumItem,
              ...styles.podiumBronze,
              height: 140,
              background: "#cd7f32",
            }}
          >
            🥉
            <h2>{podium[2][0]}</h2>
            <h3>{podium[2][1]}</h3>
          </div>
        )}
      </div>

      <div style={styles.finalBoard}>
        {visibleLeaderboard.slice(0, finalLimit).map((p, i) => (
          <div key={i} style={styles.finalRow}>
            <span>
              #{i + 1} {p[0]}
            </span>
            <span>{p[1]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}