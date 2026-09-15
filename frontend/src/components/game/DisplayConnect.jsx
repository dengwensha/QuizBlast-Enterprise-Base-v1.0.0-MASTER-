export default function DisplayConnect({ roomPin, setRoomPin, connectDisplay, setMode, styles }) {
  return (
    <div style={styles.splash}>
      <div style={styles.joinCard}>
        <h1>📺 Display Screen</h1>

        <input
          placeholder="Room PIN"
          value={roomPin}
          onChange={(e) => setRoomPin(e.target.value)}
          style={styles.input}
        />

        <button onClick={connectDisplay} style={styles.joinButton}>
          Connect Display
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