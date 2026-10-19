import { Button } from './ui/button';
import { Empty, EmptyHeader, EmptyTitle, EmptyDescription } from './ui/empty';

interface EmptyStateProps {
  onAdd: () => void;
}

export function EmptyState({ onAdd }: EmptyStateProps) {
  return (
    <Empty className="animate-fade-in bg-surface">
      <EmptyHeader>
        <p className="kicker">the board</p>
        <EmptyTitle className="font-display text-xl tracking-tight">
          No opportunities yet
        </EmptyTitle>
        <EmptyDescription>
          Start tracking hackathons, internships, and certifications. Add your
          first opportunity and it lands here, sorted by deadline.
        </EmptyDescription>
      </EmptyHeader>
      <Button onClick={onAdd} className="rounded-full">
        + Add first opportunity
      </Button>
    </Empty>
  );
}
