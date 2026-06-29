export default function JoinScreen({
  roomPin,
  setRoomPin,
  name,
  setName,
  joinRoom,
  setMode,
  styles,
}) {
  return (
    <div style={styles.splash}>
      <div style={styles.joinCard}>
        <h1>Join Game</h1>

        <input
          placeholder="Room PIN"
          value={roomPin}
          onChange={(e) => setRoomPin(e.target.value)}
          style={styles.input}
        />

        <input
          placeholder="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          style={styles.input}
        />

        {roomPin && (
          <p style={{ color: "green" }}>
            QR ile PIN otomatik dolduruldu
          </p>
        )}

        <button onClick={joinRoom} style={styles.joinButton}>
          Join
        </button>

        <button
          onClick={() => setMode(null)}
          style={{
            ...styles.joinButton,
            marginTop: 10,
            background: "#333",
          }}
        >
          Ana Menü
        </button>
      </div>
    </div>
  );
}