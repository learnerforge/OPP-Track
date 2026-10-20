import { isLoggedIn, logout } from "../auth";
import { navigate } from "../router";

/** Shared top bar — adapts its links to the session state. */
export default function Nav() {
  const authed = isLoggedIn();

  return (
    <header className="border-b border-rule bg-paper-raised">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <button
          onClick={() => navigate("/")}
          className="font-display text-lg font-semibold tracking-tight text-ink"
        >
          OppTrack
        </button>

        <nav className="flex items-center gap-5 text-sm">
          <button
            onClick={() => navigate("/")}
            className="text-ink-soft hover:text-ink"
          >
            Home
          </button>
          {authed ? (
            <>
              <button
                onClick={() => navigate("/events")}
                className="text-ink-soft hover:text-ink"
              >
                Events
              </button>
              <button
                onClick={() => {
                  logout();
                  navigate("/");
                }}
                className="rounded-md border border-rule-strong px-3 py-1.5 text-ink-soft hover:bg-paper"
              >
                Log out
              </button>
            </>
          ) : (
            <button
              onClick={() => navigate("/login")}
              className="rounded-md bg-ink px-3 py-1.5 text-paper hover:opacity-90"
            >
              Log in
            </button>
          )}
        </nav>
      </div>
    </header>
  );
}
