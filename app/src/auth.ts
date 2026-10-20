/**
 * Single-user auth for the public 3-page app (UI gate only).
 *
 * The credentials live here as a SHA-256 digest so the plaintext password is
 * never shipped in the JS bundle. A session flag is written to localStorage
 * and re-checked on every gated render.
 *
 * NOTE (fullstack.md): this gates the *UI* only — the underlying catalog stays
 * publicly readable via /api/* and /data/*. This is not real security and is
 * documented as such.
 */

const SESSION_KEY = "opptrack.session.v1";
const USERNAME = "learnerforge";
// sha256("Ganesh@2006")
const PASSWORD_SHA256 = "cb74af387f52c1a879faa59cd011283c906699475b94faba08fece94b57ff1fb";

/** Hash a string to lowercase hex via the Web Crypto API. */
async function sha256Hex(input: string): Promise<string> {
  const bytes = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/** Attempt a login. Returns true only when username AND password digest match. */
export async function login(username: string, password: string): Promise<boolean> {
  if (username.trim().toLowerCase() !== USERNAME) return false;
  const digest = await sha256Hex(password);
  if (digest !== PASSWORD_SHA256) return false;
  const payload = btoa(
    JSON.stringify({ u: USERNAME, at: Date.now() }),
  );
  localStorage.setItem(SESSION_KEY, payload);
  return true;
}

/** Clear the session flag. */
export function logout(): void {
  localStorage.removeItem(SESSION_KEY);
}

/** True when a session flag is present and structurally valid. */
export function isLoggedIn(): boolean {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return false;
    const parsed = JSON.parse(atob(raw));
    return typeof parsed === "object" && parsed !== null && parsed.u === USERNAME;
  } catch {
    return false;
  }
}
