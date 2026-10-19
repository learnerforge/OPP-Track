import { Link } from 'react-router-dom';
import { Header } from '@/components/Header';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';

const FEATURES = [
  {
    kicker: '01 · track',
    title: 'Every deadline, one ledger',
    body: 'Log hackathons, internships, certifications, and competitions the moment you find them. OppTrack sorts by urgency so the thing due tomorrow is always at the top.',
  },
  {
    kicker: '02 · sort',
    title: 'Filters that think like you',
    body: 'Search by title, slice by type, status, source platform, or tag. Narrow to “due within 7 days” and the noise disappears.',
  },
  {
    kicker: '03 · review',
    title: 'A weekly reckoning',
    body: 'A weekly review mode surfaces what is closing, what slipped, and what deserves an hour of your attention before Friday.',
  },
];

const STEPS = [
  { n: '01', label: 'Create an account', body: 'Email and password, powered by Supabase Auth. Your data lives in your own row-level-secured schema.' },
  { n: '02', label: 'Log the opportunity', body: 'Title, type, deadline, link, eligibility, tags. Thirty seconds now saves a missed application later.' },
  { n: '03', label: 'Work the countdown', body: 'Status chips move from not started → applied → done. The archive keeps the receipts.' },
];

const STATS = [
  { value: '4', label: 'event types' },
  { value: '7', label: 'urgency signals' },
  { value: '∞', label: 'deadlines tamed' },
  { value: '0', label: 'missed forms' },
];

export function Landing() {
  const { session } = useAuth();

  return (
    <div className="min-h-screen bg-paper">
      <Header />

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-4 pb-16 pt-14 sm:px-6 sm:pb-24 sm:pt-20">
        <p className="kicker mb-5">opp-track · an event website</p>
        <h1 className="max-w-4xl font-display text-4xl font-bold leading-[1.04] tracking-tight text-ink sm:text-6xl lg:text-7xl">
          The deadline is not going to
          <span className="italic-accent text-ink-soft"> remind you.</span>
        </h1>
        <p className="mt-6 max-w-2xl text-base leading-relaxed text-ink-soft sm:text-lg">
          OppTrack is where hackathons, internships, certifications, and
          competitions go to be remembered. Create an account, log what matters,
          and let the countdown do the nagging.
        </p>

        <div className="mt-8 flex flex-wrap items-center gap-3">
          {session ? (
            <Button size="lg" asChild>
              <Link to="/dashboard">Open your dashboard →</Link>
            </Button>
          ) : (
            <>
              <Button size="lg" asChild>
                <Link to="/auth?mode=signup">Create an account</Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <Link to="/auth">Sign in</Link>
              </Button>
            </>
          )}
          <span className="font-mono text-xs text-ink-faint">
            free · supabase-backed · vercel-ready
          </span>
        </div>
      </section>

      {/* Stat band */}
      <section
        aria-label="Highlights"
        className="border-y border-rule bg-ink text-paper"
      >
        <div className="mx-auto grid max-w-6xl grid-cols-2 gap-px sm:grid-cols-4">
          {STATS.map(s => (
            <div key={s.label} className="px-4 py-7 sm:px-6 sm:py-9">
              <p className="font-display text-4xl font-bold tracking-tight sm:text-5xl">
                {s.value}
              </p>
              <p className="mt-1.5 font-mono text-[11px] uppercase tracking-[0.14em] text-paper/60">
                {s.label}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-24">
        <p className="kicker mb-8">what it does</p>
        <div className="grid gap-px overflow-hidden rounded-xl border border-rule bg-rule md:grid-cols-3">
          {FEATURES.map(f => (
            <article key={f.kicker} className="bg-surface p-6 sm:p-8">
              <p className="kicker mb-4">{f.kicker}</p>
              <h3 className="font-display text-xl font-semibold leading-snug tracking-tight text-ink">
                {f.title}
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-ink-soft">
                {f.body}
              </p>
            </article>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="border-t border-rule bg-paper-raised">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-24">
          <p className="kicker mb-8">how it works</p>
          <ol className="grid gap-8 md:grid-cols-3">
            {STEPS.map(step => (
              <li key={step.n} className="border-t-2 border-ink pt-4">
                <span className="font-mono text-sm text-ink-faint">
                  {step.n}
                </span>
                <h3 className="mt-2 font-display text-lg font-semibold tracking-tight text-ink">
                  {step.label}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-soft">
                  {step.body}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-rule">
        <div className="mx-auto flex max-w-6xl flex-col items-start gap-6 px-4 py-16 sm:px-6 sm:py-20">
          <h2 className="max-w-2xl font-display text-3xl font-bold leading-tight tracking-tight text-ink sm:text-4xl">
            Stop keeping deadlines in your head.
          </h2>
          <div className="flex flex-wrap gap-3">
            {session ? (
              <Button size="lg" asChild>
                <Link to="/dashboard">Go to dashboard →</Link>
              </Button>
            ) : (
              <Button size="lg" asChild>
                <Link to="/auth?mode=signup">Get started — it takes 10 seconds</Link>
              </Button>
            )}
          </div>
        </div>
      </section>

      <footer className="border-t border-rule">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-8 font-mono text-[11px] text-ink-faint sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <span>OppTrack — events, sorted.</span>
          <span>React · Supabase · Vercel</span>
        </div>
      </footer>
    </div>
  );
}
