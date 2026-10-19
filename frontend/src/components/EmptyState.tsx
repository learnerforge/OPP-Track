import { Button } from '@/components/ui/button';

interface EmptyStateProps {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-rule bg-surface px-6 py-16 text-center">
      <span
        className="mb-4 font-mono text-3xl text-ink-faint"
        aria-hidden="true"
      >
        ◆
      </span>
      <h3 className="font-display text-lg font-semibold tracking-tight text-ink">
        {title}
      </h3>
      <p className="mt-2 max-w-sm text-sm leading-relaxed text-ink-muted">
        {description}
      </p>
      {actionLabel && onAction && (
        <Button className="mt-5" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
}
