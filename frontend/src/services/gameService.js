import { API } from "./api";

function createAuthorizationHeaders(token) {
  return {
    Authorization: `Bearer ${token}`,
  };
}

export async function createRoomRequest(quizId, token) {
  const response = await fetch(
    `${API}/create-room/${quizId}`,
    {
      method: "POST",
      headers: createAuthorizationHeaders(token),
    }
  );

  return response.json();
}

export async function startGameRequest(roomPin, token) {
  const response = await fetch(
    `${API}/start-game/${roomPin}`,
    {
      method: "POST",
      headers: createAuthorizationHeaders(token),
    }
  );

  return response.json();
}

export async function nextQuestionRequest(roomPin, token) {
  const response = await fetch(
    `${API}/next-question/${roomPin}`,
    {
      method: "POST",
      headers: createAuthorizationHeaders(token),
    }
  );

  return response.json();
}
