import { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { isSupabaseConfigured } from '@/lib/supabase';
import { Header } from '@/components/Header';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

type Mode = 'signin' | 'signup';

export function Auth() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { session, loading, signIn, signUp } = useAuth();

  const initialMode: Mode =
    searchParams.get('mode') === 'signup' ? 'signup' : 'signin';
  const [mode, setMode] = useState<Mode>(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const emailRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const t = setTimeout(() => emailRef.current?.focus(), 60);
    return () => clearTimeout(t);
  }, []);

  // Already signed in → straight to the dashboard.
  useEffect(() => {
    if (!loading && session) navigate('/dashboard', { replace: true });
  }, [session, loading, navigate]);

  function switchMode(next: Mode) {
    setMode(next);
    setError(null);
    setNotice(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setNotice(null);

    if (!email.trim()) {
      setError('Email is required.');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    setSubmitting(true);
    try {
      if (mode === 'signup') {
        const result = await signUp(email.trim(), password);
        if (result.error) {
          setError(result.error);
        } else if (result.needsConfirmation) {
          setNotice(
            'Check your inbox — we sent a confirmation link. Confirm, then sign in.'
          );
          setMode('signin');
        } else {
          // Auto-signed-in (email confirmation disabled).
          navigate('/dashboard', { replace: true });
        }
      } else {
        const result = await signIn(email.trim(), password);
        if (result.error) {
          setError(result.error);
        } else {
          navigate('/dashboard', { replace: true });
        }
      }
    } finally {
      setSubmitting(false);
    }
  }

  const isSignup = mode === 'signup';

  return (
    <div className="min-h-screen bg-paper">
      <Header />

      <main className="mx-auto grid max-w-6xl gap-12 px-4 py-14 sm:px-6 lg:grid-cols-2 lg:gap-16 lg:py-20">
        {/* Pitch column */}
        <div className="flex flex-col justify-center">
          <p className="kicker mb-5">
            {isSignup ? 'new account' : 'welcome back'}
          </p>
          <h1 className="font-display text-4xl font-bold leading-[1.05] tracking-tight text-ink sm:text-5xl">
            {isSignup ? (
              <>
                Start keeping deadlines
                <span className="italic-accent text-ink-soft"> out of your head.</span>
              </>
            ) : (
              <>
                Your deadlines
                <span className="italic-accent text-ink-soft"> kept waiting.</span>
              </>
            )}
          </h1>
          <p className="mt-5 max-w-md text-base leading-relaxed text-ink-soft">
            {isSignup
              ? 'One account, one ledger. Every hackathon and application you log stays private to you, secured by row-level security in Supabase.'
              : 'Sign in to pick up where you left off — the countdown never stopped.'}
          </p>

          <ul className="mt-8 space-y-3">
            {[
              'Per-user data with row-level security',
              'Urgency sorting: due today, this week, this month',
              'Status tracking from “not started” to “done”',
            ].map(item => (
              <li key={item} className="flex items-start gap-2.5 text-sm text-ink-soft">
                <span className="mt-0.5 font-mono text-ink-faint" aria-hidden="true">
                  ✓
                </span>
                {item}
              </li>
            ))}
          </ul>
        </div>

        {/* Form column */}
        <div className="flex items-center">
          <div className="w-full rounded-xl border border-rule bg-surface p-6 shadow-sm sm:p-8">
            <div className="mb-6 flex items-baseline justify-between gap-4 border-b border-rule pb-4">
              <h2 className="font-display text-xl font-semibold tracking-tight text-ink">
                {isSignup ? 'Create account' : 'Sign in'}
              </h2>
              <button
                type="button"
                onClick={() => switchMode(isSignup ? 'signin' : 'signup')}
                className="font-mono text-xs text-accent underline-offset-4 hover:underline focus-ring rounded"
              >
                {isSignup ? 'I already have an account →' : 'New here? Create one →'}
              </button>
            </div>

            {!isSupabaseConfigured && (
              <Alert className="mb-5 border-warning/40 bg-warning-soft">
                <AlertTitle className="text-warning">
                  Supabase not configured
                </AlertTitle>
                <AlertDescription className="text-ink-soft">
                  Set <code className="font-mono text-xs">VITE_SUPABASE_URL</code>{' '}
                  and{' '}
                  <code className="font-mono text-xs">VITE_SUPABASE_ANON_KEY</code>{' '}
                  (see <code className="font-mono text-xs">.env.example</code>), then
                  run <code className="font-mono text-xs">supabase/schema.sql</code> in
                  the SQL editor.
                </AlertDescription>
              </Alert>
            )}

            {error && (
              <Alert variant="destructive" className="mb-5" role="alert">
                <AlertTitle>Sign {isSignup ? 'up' : 'in'} failed</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {notice && (
              <Alert className="mb-5 border-safe/40 bg-safe-soft" role="status">
                <AlertTitle className="text-safe">Almost there</AlertTitle>
                <AlertDescription className="text-ink-soft">
                  {notice}
                </AlertDescription>
              </Alert>
            )}

            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              <div className="space-y-1.5">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  ref={emailRef}
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  aria-invalid={!!error && !email.trim()}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete={isSignup ? 'new-password' : 'current-password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder={isSignup ? 'At least 6 characters' : 'Your password'}
                  required
                  aria-invalid={!!error && password.length < 6}
                />
                {isSignup && (
                  <p className="font-mono text-[11px] text-ink-faint">
                    minimum 6 characters
                  </p>
                )}
              </div>

              <Button
                type="submit"
                className="w-full"
                size="lg"
                disabled={submitting}
                aria-busy={submitting}
              >
                {submitting
                  ? 'Working…'
                  : isSignup
                    ? 'Create account'
                    : 'Sign in'}
              </Button>
            </form>

            <p className="mt-6 border-t border-rule pt-4 text-center font-mono text-[11px] text-ink-faint">
              Auth powered by Supabase ·{' '}
              <Link
                to="/"
                className="underline-offset-4 hover:underline focus-ring rounded"
              >
                back to home
              </Link>
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
