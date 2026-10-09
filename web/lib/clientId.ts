const KEY = "learnio.client_id";

function makeId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "c-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
}

/** Generate once, persist in localStorage. Call from the browser only (e.g. in an effect). */
export function getClientId(): string {
  try {
    const existing = window.localStorage.getItem(KEY);
    if (existing) return existing;
  } catch {
    // storage unavailable; fall through
  }
  const id = makeId();
  try {
    window.localStorage.setItem(KEY, id);
  } catch {
    // ignore: id lives for this page load only
  }
  return id;
}
