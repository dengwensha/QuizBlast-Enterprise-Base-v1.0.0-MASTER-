export function normalizeQuestionImage(value) {
  if (typeof value !== "string") return "";

  const candidate = value.trim();

  if (!candidate) return "";

  if (
    /^https?:\/\//i.test(candidate) ||
    /^data:image\//i.test(candidate) ||
    /^blob:/i.test(candidate) ||
    candidate.startsWith("/")
  ) {
    return candidate;
  }

  return "";
}
