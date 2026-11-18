import React from "react";
import "./leaderboard-board.css";

export default function LeaderboardBoard({ visibleLeaderboard, live = false, styles }) {
  return (
    <div style={live ? styles.liveBoard : styles.board}>
      <h2>🏆 Leaderboard</h2>

      {visibleLeaderboard.map((p, i) => (
        <div
          key={i}
          className="qb-leaderboard-board__row"
          style={live ? styles.liveBoardRow : styles.boardRow}
        >
          <span>
            #{i + 1} {p[0]}
          </span>
          <span>{p[1]}</span>
        </div>
      ))}
    </div>
  );
}