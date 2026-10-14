import React from "react";

import QuestionList from "../question/QuestionList";
import "./host-setup.css";

const roomStatusLabel = {
  lobby: "Bekliyor",
  question: "Aktif",
  result: "Aktif",
  paused: "Duraklatıldı",
  completed: "Tamamlandı",
};

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
  hostRooms,
  hostRoomsError,
  returnToRoom,
}) {
  return (
    <div className="qb-host-setup">
      <div className="qb-host-setup__header">
        <h1>Host Dashboard 🚀</h1>

        <button
          onClick={() => setMode(null)}
          className="qb-host-setup__action qb-host-setup__back"
        >
          Ana Menü
        </button>
      </div>

      <div className="qb-host-setup__content">
        {hostRooms.length > 0 && <div className="qb-host-setup__panel">
          <h2>Açık odalarım</h2>
          {hostRooms.map(room => <div key={room.instance_id} className="qb-host-setup__room">
            <span className="qb-host-setup__room-meta">PIN: {room.pin} · Quiz #{room.quiz_id} · {roomStatusLabel[room.status || room.phase] || room.status || room.phase}</span>
            <button type="button" onClick={() => returnToRoom(room)} className="qb-host-setup__action qb-host-setup__return">
              Odaya Dön
            </button>
          </div>)}
        </div>}
        {hostRoomsError && <p role="alert">Açık odalar yüklenemedi. Sayfayı yenileyip tekrar deneyin.</p>}
        <div className="qb-host-setup__panel">
          <h2>Quiz Seç</h2>

          <select
            value={selectedQuizId}
            onChange={(e) => {
              setSelectedQuizId(e.target.value);
              loadSelectedQuestions(e.target.value);
            }}
            className="qb-host-setup__input"
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
            className="qb-host-setup__action qb-host-setup__primary"
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

