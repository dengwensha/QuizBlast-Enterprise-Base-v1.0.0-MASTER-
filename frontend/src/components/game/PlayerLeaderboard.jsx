import React from "react";

import { Card } from "../ui";
import "./player-leaderboard.css";

export default function PlayerLeaderboard({ visibleLeaderboard = [] }) {
  return (
    <Card className="qb-player-leaderboard" aria-label="Leaderboard">
      <div className="qb-player-leaderboard__heading">
        <span aria-hidden="true">🏆</span>
        <h2>Leaderboard</h2>
      </div>
      <div className="qb-player-leaderboard__rows">
        {visibleLeaderboard.map((player, index) => (
          <div className="qb-player-leaderboard__row" key={`${player[0]}-${index}`}>
            <span className="qb-player-leaderboard__player">#{index + 1} {player[0]}</span>
            <span className="qb-player-leaderboard__score">{player[1]}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
