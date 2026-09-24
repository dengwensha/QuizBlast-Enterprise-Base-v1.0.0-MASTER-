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

  const [players, setPlayers] = useState([]);
  const [question, setQuestion] = useState(null);
  const [questionImage, setQuestionImage] = useState("");
  const [options, setOptions] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [questionResult, setQuestionResult] = useState(null);
  const [timeLeft, setTimeLeft] = useState(0);
  const [answered, setAnswered] = useState(false);
  const [gameOver, setGameOver] = useState(false);
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
    setAnswerCount(0);
    setTotalPlayers(0);
    setCurrentQuestionIndex(0);
  };

  const closeSocket = () => {
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
    resetGame();
  };

  const connectWebsocket = (pin, who, hostToken) => {
    closeSocket();
    setJoined(false);
    setPlayerName(who);

    const ws = new WebSocket(
      `${WS}/ws/${pin}/${encodeURIComponent(who)}`,
      who === "HOST" && hostToken
        ? ["quizblast-host", hostToken]
        : undefined
    );

    ws.onopen = () => {};

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "join_error") {
        alert(
          data.reason === "duplicate_name"
            ? "Bu isim zaten odada. Farklı bir isim gir."
            : data.reason === "room_not_found"
              ? "Oda bulunamadı. PIN kontrol et."
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

      if (data.type === "players") {
        setJoined(true);
        setPlayers(data.players);

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
        setTimeLeft(data.time);
        setAnswered(false);
        setGameOver(false);
        setAnswerCount(0);
      }

      if (data.type === "answer_count") {
        setAnswerCount(data.count);
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
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error", error);
    };

    socketRef.current = ws;
    setSocket(ws);
  };

  const sendAnswer = (answerIndex) => {
    const activeSocket = socketRef.current || socket;

    if (
      !activeSocket ||
      activeSocket.readyState !== WebSocket.OPEN ||
      answered ||
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
    if (!joined || timeLeft <= 0) {
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
  }, [joined, timeLeft]);

  useEffect(() => {
    return () => {
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
    players,
    question,
    questionImage,
    options,
    leaderboard,
    currentQuestionIndex,
    questionResult,
    timeLeft,
    answered,
    gameOver,
    answerCount,
    totalPlayers,
    connectWebsocket,
    sendAnswer,
    resetGame,
    closeSession,
  };
}
