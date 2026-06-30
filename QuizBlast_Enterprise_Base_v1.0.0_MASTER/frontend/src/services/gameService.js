import { API } from "./api";

export async function createRoomRequest(quizId) {
  const r = await fetch(`${API}/create-room/${quizId}`);
  return await r.json();
}