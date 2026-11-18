import { API, authHeaders } from "./api";

async function readResponse(response) {
  const body = await response.json().catch(() => ({}));
  if (!response.ok || body.error || body.detail) {
    throw new Error(body.detail || body.error || "İşlem tamamlanamadı.");
  }
  return body;
}

export async function fetchContentSets() {
  return readResponse(await fetch(`${API}/content/sets`));
}

export async function fetchContentSetPreview(setId) {
  return readResponse(await fetch(`${API}/content/sets/${encodeURIComponent(setId)}/preview`));
}

export async function copyContentSet(user, setId) {
  return readResponse(await fetch(`${API}/content/sets/${encodeURIComponent(setId)}/copy`, {
    method: "POST",
    headers: authHeaders(user),
  }));
}
