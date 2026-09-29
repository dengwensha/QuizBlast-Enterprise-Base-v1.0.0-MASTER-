import React from "react";

import { Card } from "../ui";
import "./player-game-over.css";

export default function PlayerGameOver({ podium = [], visibleLeaderboard = [], finalLimit }) {
  const finalists = visibleLeaderboard.slice(0, finalLimit);

  return (
    <section className="qb-player-game-over" aria-label="Oyun sonucu">
      <p className="qb-player-game-over__eyebrow">Final</p>
      <h1 className="qb-player-game-over__title">GAME OVER 🎉</h1>
      <div className="qb-player-game-over__podium" aria-label="Podyum">
        {podium[0] && <Card className="qb-player-game-over__winner"><span aria-hidden="true">👑</span><strong>{podium[0][0]}</strong><span>{podium[0][1]}</span></Card>}
        <div className="qb-player-game-over__runner-ups">
          {podium[1] && <Card><span aria-hidden="true">🥈</span><strong>{podium[1][0]}</strong><span>{podium[1][1]}</span></Card>}
          {podium[2] && <Card><span aria-hidden="true">🥉</span><strong>{podium[2][0]}</strong><span>{podium[2][1]}</span></Card>}
        </div>
      </div>
      <Card className="qb-player-game-over__board">
        <h2>Final Sıralaması</h2>
        <div className="qb-player-game-over__rows">
          {finalists.map((player, index) => (
            <div className="qb-player-game-over__row" key={`${player[0]}-${index}`}>
              <span>#{index + 1} {player[0]}</span>
              <span>{player[1]}</span>
            </div>
          ))}
        </div>
      </Card>
    </section>
  );
}
