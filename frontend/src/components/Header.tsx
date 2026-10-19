import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';

interface HeaderProps {
  onNewEntry?: () => void;
}

export function Header({ onNewEntry }: HeaderProps) {
  const { session, signOut } = useAuth();
  const navigate = useNavigate();

  async function handleSignOut() {
    await signOut();
    navigate('/');
  }

  const email = session?.user?.email;

  return (
    <header className="sticky top-0 z-40 border-b border-rule bg-paper/90 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link
          to="/"
          className="group flex items-baseline gap-2 focus-ring rounded"
          aria-label="OppTrack home"
        >
          <span className="font-display text-xl font-bold tracking-tight text-ink">
            Opp<span className="italic-accent font-normal">Track</span>
          </span>
          <span className="hidden font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint sm:inline">
            events, sorted
          </span>
        </Link>

        <nav className="flex items-center gap-2 sm:gap-3">
          {onNewEntry && (
            <Button
              size="sm"
              onClick={onNewEntry}
              aria-label="Add a new opportunity"
              className="hidden sm:inline-flex"
            >
              + New entry
            </Button>
          )}

          {session ? (
            <>
              {email && (
                <span
                  className="hidden max-w-[180px] truncate font-mono text-xs text-ink-muted md:inline"
                  title={email}
                >
                  {email}
                </span>
              )}
              <Button
                size="sm"
                variant="outline"
                onClick={handleSignOut}
                aria-label="Sign out"
              >
                Sign out
              </Button>
            </>
          ) : (
            <>
              <Button size="sm" variant="ghost" asChild>
                <Link to="/auth">Sign in</Link>
              </Button>
              <Button size="sm" asChild>
                <Link to="/auth?mode=signup">Create account</Link>
              </Button>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
