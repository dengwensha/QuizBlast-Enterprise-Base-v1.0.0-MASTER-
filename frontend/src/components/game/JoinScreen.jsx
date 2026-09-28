import React from "react";

import { Button, Card, Input } from "../ui";
import "./join-screen.css";

export default function JoinScreen({
  roomPin,
  setRoomPin,
  name,
  setName,
  joinRoom,
  setMode,
}) {
  return (
    <main className="qb-player-join">
      <Card className="qb-player-join__card">
        <div className="qb-player-join__brand">QuizBlast</div>
        <h1 className="qb-player-join__title">Join Game</h1>
        <p className="qb-player-join__intro">
          Enter the game PIN and the name you want other players to see.
        </p>

        <div className="qb-player-join__form">
          <Input
            id="game-pin"
            label="Game PIN"
            placeholder="Room PIN"
            inputMode="numeric"
            autoComplete="off"
            value={roomPin}
            onChange={(event) => setRoomPin(event.target.value)}
          />

          {roomPin && (
            <p className="qb-player-join__hint" role="status">
              PIN hazır. QR bağlantısı kullandıysan otomatik doldurulmuş olabilir.
            </p>
          )}

          <Input
            id="player-name"
            label="Nickname"
            placeholder="Name"
            autoComplete="nickname"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />

          <Button type="button" size="lg" fullWidth onClick={joinRoom}>
            Join
          </Button>

          <Button
            type="button"
            variant="ghost"
            fullWidth
            onClick={() => setMode(null)}
          >
            Ana Menü
          </Button>
        </div>
      </Card>
    </main>
  );
}
