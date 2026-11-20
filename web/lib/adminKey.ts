const KEY = "learnio.admin_key";

/** The admin key saved in this browser, if any. Call from the browser only. */
export function getAdminKey(): string | null {
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setAdminKey(value: string | null): void {
  try {
    if (value) window.localStorage.setItem(KEY, value);
    else window.localStorage.removeItem(KEY);
  } catch {
    // storage unavailable: the key lasts for this page load only
  }
}
