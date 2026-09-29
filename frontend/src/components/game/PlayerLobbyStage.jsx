import React from "react";

import { Card } from "../ui";
import "./player-lobby-stage.css";

export default function PlayerLobbyStage({ roomPin, playerName, players = [] }) {
  return (
    <section className="qb-player-lobby" aria-label="Oyun lobisi">
      <Card className="qb-player-lobby__card">
        <p className="qb-player-lobby__eyebrow">Oyuna katıldın</p>
        <h1 className="qb-player-lobby__title">Oyuncular Bekleniyor...</h1>
        <p className="qb-player-lobby__message">Host oyunu başlattığında ilk soru burada görünecek.</p>
        <div className="qb-player-lobby__identity">
          <span>PIN <strong>{roomPin}</strong></span>
          {playerName && <span>Oyuncu <strong>{playerName}</strong></span>}
        </div>
      </Card>
      <Card className="qb-player-lobby__players">
        <div className="qb-player-lobby__players-heading">
          <h2>Oyuncular</h2>
          <span>{players.length}</span>
        </div>
        <div className="qb-player-lobby__roster">
          {players.map((player, index) => <div key={`${player}-${index}`} className="qb-player-lobby__player">👤 {player}</div>)}
        </div>
      </Card>
    </section>
  );
}
