import { API, authHeaders, jsonAuthHeaders } from "./api";

export async function fetchQuizzes(user) {
  const r = await fetch(`${API}/quizzes`, {
    headers: authHeaders(user),
  });

  const d = await r.json();
  return Array.isArray(d) ? d : [];
}

export async function fetchQuizQuestions(user, quizId) {
  if (!quizId) return [];

  const r = await fetch(`${API}/quizzes/${quizId}/questions`, {
    headers: authHeaders(user),
  });

  const d = await r.json();
  return Array.isArray(d) ? d : [];
}

export async function createQuizRequest(user, title) {
  const r = await fetch(`${API}/quizzes`, {
    method: "POST",
    headers: jsonAuthHeaders(user),
    body: JSON.stringify({ title }),
  });

  return await r.json();
}

export async function deleteQuizRequest(user, quizId) {
  await fetch(`${API}/quizzes/${quizId}`, {
    method: "DELETE",
    headers: authHeaders(user),
  });
}
export async function addQuestionRequest(user, quizId, payload) {
  const r = await fetch(`${API}/quizzes/${quizId}/questions`, {
    method: "POST",
    headers: jsonAuthHeaders(user),
    body: JSON.stringify(payload),
  });

  return await r.json();
}