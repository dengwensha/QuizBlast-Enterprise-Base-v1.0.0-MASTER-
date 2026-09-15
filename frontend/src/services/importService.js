import {
  API,
  authHeaders,
  jsonAuthHeaders,
} from "./api";

export async function previewImportRequest(user, quizId, file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API}/quizzes/${quizId}/import/preview`, {
    method: "POST",
    headers: authHeaders(user),
    body: formData,
  });

  return response.json();
}

export async function commitImportRequest(user, quizId, payload) {
  const response = await fetch(`${API}/quizzes/${quizId}/import/commit`, {
    method: "POST",
    headers: jsonAuthHeaders(user),
    body: JSON.stringify(payload),
  });

  return response.json();
}
