import { useState } from "react";
import Nav from "../components/Nav";
import { login } from "../auth";
import { navigate } from "../router";

/** Public login page — single user, digest-checked in the browser. */
export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const ok = await login(username, password);
    setBusy(false);
    if (ok) {
      navigate("/events");
    } else {
      setError("Invalid username or password.");
    }
  }

  return (
    <>
      <Nav />
      <main className="mx-auto flex max-w-md flex-col px-6 py-20">
        <p className="font-mono text-xs uppercase tracking-widest text-ink-muted">
          Members
        </p>
        <h1 className="mt-3 font-display text-3xl font-bold tracking-tight text-ink">
          Log in
        </h1>
        <p className="mt-3 text-sm text-ink-muted">
          Sign in to view the full events catalog.
        </p>

        <form
          onSubmit={onSubmit}
          className="mt-8 rounded-lg border border-rule bg-surface p-6"
        >
          <label className="block text-sm font-medium text-ink-soft">
            Username
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              className="mt-1.5 w-full rounded-md border border-rule-strong bg-paper-raised px-3 py-2 text-ink outline-none focus:border-accent"
            />
          </label>

          <label className="mt-4 block text-sm font-medium text-ink-soft">
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              className="mt-1.5 w-full rounded-md border border-rule-strong bg-paper-raised px-3 py-2 text-ink outline-none focus:border-accent"
            />
          </label>

          {error && (
            <p className="mt-4 rounded-md bg-critical-soft px-3 py-2 text-sm text-critical">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy}
            className="mt-6 w-full rounded-md bg-ink px-4 py-2.5 font-medium text-paper hover:opacity-90 disabled:opacity-60"
          >
            {busy ? "Checking…" : "Log in"}
          </button>
        </form>
      </main>
    </>
  );
}
