import { useEffect, useRef, useState } from "react";

import { WS } from "../services/api";

export function useGameSession({
  onQuestion,
  onQuestionResult,
  onGameOver,
  onCountdown,
} = {}) {
  const callbacksRef = useRef({
    onQuestion,
    onQuestionResult,
    onGameOver,
    onCountdown,
  });

  callbacksRef.current = {
    onQuestion,
    onQuestionResult,
    onGameOver,
    onCountdown,
  };

  const [roomPin, setRoomPin] = useState(
    () => new URLSearchParams(window.location.search).get("pin") || ""
  );
  const [name, setName] = useState("");
  const [playerName, setPlayerName] = useState("");
  const [joined, setJoined] = useState(false);
  const [socket, setSocket] = useState(null);
  const socketRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const connectionRef = useRef(null);
  const [reconnecting, setReconnecting] = useState(false);

  const [players, setPlayers] = useState([]);
  const [question, setQuestion] = useState(null);
  const [questionImage, setQuestionImage] = useState("");
  const [options, setOptions] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [questionResult, setQuestionResult] = useState(null);
  const [timeLeft, setTimeLeft] = useState(0);
  const [answered, setAnswered] = useState(false);
  const [gameOver, setGameOver] = useState(false);
  const [paused, setPaused] = useState(false);
  const [answerCount, setAnswerCount] = useState(0);
  const [totalPlayers, setTotalPlayers] = useState(0);

  const resetGame = () => {
    setJoined(false);
    setRoomPin("");
    setName("");
    setPlayerName("");
    setPlayers([]);
    setQuestion(null);
    setQuestionImage("");
    setOptions([]);
    setLeaderboard([]);
    setQuestionResult(null);
    setTimeLeft(0);
    setAnswered(false);
    setGameOver(false);
    setPaused(false);
    setAnswerCount(0);
    setTotalPlayers(0);
    setCurrentQuestionIndex(0);
    setTotalQuestions(0);
  };

  const closeSocket = () => {
    connectionRef.current = null;
    clearTimeout(reconnectTimerRef.current);
    setReconnecting(false);
    const activeSocket = socketRef.current;

    if (activeSocket) {
      try {
        activeSocket.close();
      } catch (error) {
        console.error("WebSocket close error", error);
      }
    }

    socketRef.current = null;
    setSocket(null);
  };

  const closeSession = () => {
    closeSocket();
    sessionStorage.removeItem("quizblast_active_session");
    resetGame();
  };

  const connectWebsocket = (pin, who, hostToken) => {
    closeSocket();
    const connection = { pin, who, hostToken, attempt: 0 };
    connectionRef.current = connection;
    setJoined(false);
    setPlayerName(who);

    const open = () => {
    const playerKey = `quizblast_player_${pin}_${who}`;
    let playerToken = sessionStorage.getItem(playerKey);
    if (who !== "HOST" && who !== "DISPLAY" && !playerToken) {
      playerToken = Array.from(crypto.getRandomValues(new Uint8Array(32)),
        (byte) => byte.toString(16).padStart(2, "0")).join("");
      sessionStorage.setItem(playerKey, playerToken);
    }

    const ws = new WebSocket(
      `${WS}/ws/${pin}/${encodeURIComponent(who)}`,
      who === "HOST" && hostToken
        ? ["quizblast-host", hostToken]
        : who !== "DISPLAY" && playerToken
          ? ["quizblast-player", playerToken]
          : undefined
    );

    ws.onopen = () => {
      connection.attempt = 0;
      setReconnecting(false);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "join_error") {
        connectionRef.current = null;
        clearTimeout(reconnectTimerRef.current);
        setReconnecting(false);
        sessionStorage.removeItem("quizblast_active_session");
        alert(
          data.reason === "duplicate_name"
            ? "Bu isim zaten odada. Farklı bir isim gir."
            : data.reason === "room_not_found"
              ? "Oda bulunamadı. PIN kontrol et."
              : data.reason === "player_unauthorized"
                ? "Oyuncu oturumu doğrulanamadı. Önceki oyun anahtarı gerekli."
              : "Geçersiz giriş."
        );

        setJoined(false);
        socketRef.current = null;
        setSocket(null);

        try {
          ws.close();
        } catch (error) {
          console.error("WebSocket close error", error);
        }

        return;
      }

      if (data.type === "player_session") {
        sessionStorage.setItem(`quizblast_player_${pin}_${who}`, data.token);
      }

      if (data.type === "players") {
        setJoined(true);
        setPlayers(data.players);
        sessionStorage.setItem("quizblast_active_session", JSON.stringify({ pin, who }));

        setTotalPlayers(
          data.players.filter(
            (player) =>
              player !== "HOST" &&
              player !== "DISPLAY"
          ).length
        );
      }

      if (data.type === "question") {
        callbacksRef.current.onQuestion?.();

        setQuestionResult(null);
        setQuestion(data.question);
        setQuestionImage(data.image_url || "");
        setOptions(data.options);
        setCurrentQuestionIndex(data.index || 0);
        setTotalQuestions(data.question_count || 0);
        setTimeLeft(Math.ceil(data.time));
        setPaused(Boolean(data.paused));
        setAnswered(Boolean(data.answered));
        setGameOver(false);
        setAnswerCount(0);
      }

      if (data.type === "answer_count") {
        setAnswerCount(data.count);
      }

      if (data.type === "game_paused") {
        setPaused(true);
        setTimeLeft(Math.ceil(data.remaining));
      }

      if (data.type === "question_result") {
        callbacksRef.current.onQuestionResult?.();
        setQuestionResult(data);
      }

      if (data.type === "leaderboard") {
        setLeaderboard(data.scores);
      }

      if (data.type === "game_over") {
        callbacksRef.current.onGameOver?.();

        setQuestion(null);
        setQuestionImage("");
        setOptions([]);
        setGameOver(true);
      }
    };

    ws.onclose = () => {
      if (socketRef.current === ws) {
        socketRef.current = null;
        setSocket(null);
        setJoined(false);
        setTimeLeft(0);
        if (connectionRef.current === connection) {
          setReconnecting(true);
          const delay = Math.min(1000 * 2 ** connection.attempt, 5000);
          connection.attempt += 1;
          reconnectTimerRef.current = setTimeout(open, delay);
        }
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error", error);
    };

    socketRef.current = ws;
    setSocket(ws);
    };
    open();
  };

  const sendAnswer = (answerIndex) => {
    const activeSocket = socketRef.current || socket;

    if (
      !activeSocket ||
      activeSocket.readyState !== WebSocket.OPEN ||
      answered ||
      paused ||
      timeLeft <= 0
    ) {
      return;
    }

    activeSocket.send(
      JSON.stringify({
        type: "answer",
        answer: answerIndex,
        timeLeft,
      })
    );

    setAnswered(true);
  };

  useEffect(() => {
    if (!joined || paused || timeLeft <= 0) {
      return;
    }

    const timer = setTimeout(() => {
      setTimeLeft((previousTime) => {
        if (
          previousTime <= 6 &&
          previousTime > 1
        ) {
          callbacksRef.current.onCountdown?.();
        }

        return previousTime - 1;
      });
    }, 1000);

    return () => clearTimeout(timer);
  }, [joined, paused, timeLeft]);

  useEffect(() => {
    return () => {
      connectionRef.current = null;
      clearTimeout(reconnectTimerRef.current);
      const activeSocket = socketRef.current;

      if (activeSocket) {
        try {
          activeSocket.close();
        } catch (error) {
          console.error(
            "WebSocket close error",
            error
          );
        }
      }
    };
  }, []);

  return {
    roomPin,
    setRoomPin,
    name,
    setName,
    playerName,
    joined,
    reconnecting,
    players,
    question,
    questionImage,
    options,
    leaderboard,
    currentQuestionIndex,
    totalQuestions,
    questionResult,
    timeLeft,
    answered,
    gameOver,
    paused,
    answerCount,
    totalPlayers,
    connectWebsocket,
    sendAnswer,
    resetGame,
    closeSession,
  };
}
