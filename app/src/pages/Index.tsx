import Nav from "../components/Nav";
import { navigate } from "../router";
import { isLoggedIn } from "../auth";

/** Public landing page — visible to everyone. */
export default function Index() {
  const authed = isLoggedIn();

  return (
    <>
      <Nav />
      <main className="mx-auto max-w-5xl px-6 py-20">
        <p className="font-mono text-xs uppercase tracking-widest text-ink-muted">
          Public catalog
        </p>
        <h1 className="mt-3 font-display text-5xl font-bold tracking-tight text-ink">
          Opportunities, sorted.
        </h1>
        <p className="mt-5 max-w-2xl text-lg leading-relaxed text-ink-soft">
          A live catalog of hackathons, internships, competitions and
          certifications for students — refreshed automatically by a scheduled
          pipeline, checksummed, and served straight from JSON.
        </p>

        <div className="mt-8 flex flex-wrap gap-3">
          {authed ? (
            <button
              onClick={() => navigate("/events")}
              className="rounded-md bg-ink px-5 py-2.5 font-medium text-paper hover:opacity-90"
            >
              Browse events
            </button>
          ) : (
            <button
              onClick={() => navigate("/login")}
              className="rounded-md bg-ink px-5 py-2.5 font-medium text-paper hover:opacity-90"
            >
              Log in to view events
            </button>
          )}
          <a
            href="/api/health"
            className="rounded-md border border-rule-strong px-5 py-2.5 font-medium text-ink-soft hover:bg-paper-raised"
          >
            Pipeline health
          </a>
        </div>

        <dl className="mt-16 grid gap-6 sm:grid-cols-3">
          {[
            ["Scheduled engine", "Full scrape every 8 hours, published with a sha256 manifest."],
            ["Read-only API", "Filtered reads, stats and CSV export — no write surface at all."],
            ["Complete catalog", "Every item is shown; nothing is truncated or sampled."],
          ].map(([title, body]) => (
            <div key={title} className="rounded-lg border border-rule bg-surface p-5">
              <dt className="font-display font-semibold text-ink">{title}</dt>
              <dd className="mt-2 text-sm leading-relaxed text-ink-muted">{body}</dd>
            </div>
          ))}
        </dl>
      </main>
    </>
  );
}
