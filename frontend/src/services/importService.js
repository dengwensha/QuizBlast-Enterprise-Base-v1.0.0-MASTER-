import {
  API,
  authHeaders,
} from "./api";

async function readImportResponse(response) {
  const data = await response.json();

  if (!response.ok) {
    const detail = data.detail || data.error || `http_${response.status}`;

    return {
      ...data,
      error: data.error || detail,
      message: data.message || detail,
    };
  }

  return data;
}

export async function previewImportRequest(user, quizId, file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API}/quizzes/${quizId}/import/preview`, {
    method: "POST",
    headers: authHeaders(user),
    body: formData,
  });

  return readImportResponse(response);
}

export async function commitImportRequest(user, quizId, file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API}/quizzes/${quizId}/import/commit`, {
    method: "POST",
    headers: authHeaders(user),
    body: formData,
  });

  return readImportResponse(response);
}
