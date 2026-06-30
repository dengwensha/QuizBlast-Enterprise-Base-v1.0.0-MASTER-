import { API } from "./api";

export async function createRoomRequest(quizId) {
  const r = await fetch(`${API}/create-room/${quizId}`);
  return await r.json();
}
export async function startGameRequest(roomPin) {
  await fetch(`${API}/start-game/${roomPin}`);
}
export async function nextQuestionRequest(roomPin) {
  await fetch(`${API}/next-question/${roomPin}`);
}