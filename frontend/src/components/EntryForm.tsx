import { useState, useEffect, useRef } from 'react';
import type { Opportunity } from '@/types/opportunity';
import { TYPE_OPTIONS, STATUS_OPTIONS } from '@/lib/constants';
import { validateOpportunity, getFieldError } from '@/lib/validation';
import { STATUS_META, TYPE_META } from '@/lib/meta';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface EntryFormProps {
  onSave: (opp: Opportunity) => void;
  onCancel: () => void;
  initial?: Opportunity;
  isEdit?: boolean;
}

export function EntryForm({
  onSave,
  onCancel,
  initial,
  isEdit = false,
}: EntryFormProps) {
  const [form, setForm] = useState({
    title: '',
    type: 'Hackathon' as Opportunity['type'],
    source: '',
    link: '',
    deadline: '',
    eligibility: '',
    tags: '',
    status: 'Not Started' as Opportunity['status'],
    notes: '',
    ...(initial ? { ...initial, tags: initial.tags.join(', ') } : {}),
  });
  const [errors, setErrors] = useState<{ field: string; message: string }[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const titleRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const t = setTimeout(() => titleRef.current?.focus(), 60);
    return () => clearTimeout(t);
  }, []);

  function update(field: keyof typeof form, value: string) {
    setForm(prev => ({ ...prev, [field]: value }));
    setErrors(prev => prev.filter(e => e.field !== field));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const tagList = form.tags
      .split(',')
      .map(t => t.trim())
      .filter(Boolean);

    const oppData: Partial<Opportunity> = { ...form, tags: tagList };
    const validationErrors = validateOpportunity(oppData, isEdit);
    if (validationErrors.length > 0) {
      setErrors(validationErrors);
      return;
    }

    setSubmitting(true);
    try {
      const entry: Opportunity = {
        id: isEdit && initial ? initial.id : '',
        user_id: isEdit && initial ? initial.user_id : '',
        title: form.title.trim(),
        type: form.type,
        source: form.source.trim(),
        link: form.link.trim(),
        deadline: form.deadline,
        eligibility: form.eligibility.trim(),
        tags: tagList,
        status: form.status,
        notes: form.notes.trim(),
        date_added: isEdit && initial ? initial.date_added : '',
      };
      onSave(entry);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open onOpenChange={open => !open && onCancel()}>
      <DialogContent
        className="max-h-[90vh] overflow-y-auto sm:max-w-xl"
        aria-label={isEdit ? 'Edit opportunity' : 'Add new opportunity'}
      >
        <DialogHeader>
          <p className="kicker">{isEdit ? 'editing entry' : 'new entry'}</p>
          <DialogTitle className="font-display text-2xl tracking-tight">
            {isEdit ? 'Edit opportunity' : 'Add an opportunity'}
          </DialogTitle>
          <DialogDescription>
            Log it once — OppTrack handles the sorting and the countdown.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <Field label="Title" required error={getFieldError(errors, 'title')}>
            <Input
              ref={titleRef}
              type="text"
              value={form.title}
              onChange={e => update('title', e.target.value)}
              placeholder="e.g. Smart India Hackathon 2026"
              aria-invalid={!!getFieldError(errors, 'title')}
            />
          </Field>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Type" required error={getFieldError(errors, 'type')}>
              <Select value={form.type} onValueChange={v => update('type', v)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TYPE_OPTIONS.map(t => (
                    <SelectItem key={t} value={t}>
                      {TYPE_META[t].glyph} {TYPE_META[t].label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            <Field label="Status">
              <Select
                value={form.status}
                onValueChange={v => update('status', v as Opportunity['status'])}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {STATUS_OPTIONS.map(s => (
                    <SelectItem key={s} value={s}>
                      {STATUS_META[s].label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Source platform">
              <Input
                type="text"
                value={form.source}
                onChange={e => update('source', e.target.value)}
                placeholder="e.g. Unstop, Internshala"
              />
            </Field>
            <Field
              label="Deadline"
              required
              hint="IST"
              error={getFieldError(errors, 'deadline')}
            >
              <Input
                type="date"
                value={form.deadline}
                onChange={e => update('deadline', e.target.value)}
                aria-invalid={!!getFieldError(errors, 'deadline')}
              />
            </Field>
          </div>

          <Field label="Link" error={getFieldError(errors, 'link')}>
            <Input
              type="url"
              value={form.link}
              onChange={e => update('link', e.target.value)}
              placeholder="https://..."
              aria-invalid={!!getFieldError(errors, 'link')}
            />
          </Field>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Eligibility">
              <Input
                type="text"
                value={form.eligibility}
                onChange={e => update('eligibility', e.target.value)}
                placeholder="e.g. 3rd year, teams of 4"
              />
            </Field>
            <Field label="Tags" hint="comma-separated">
              <Input
                type="text"
                value={form.tags}
                onChange={e => update('tags', e.target.value)}
                placeholder="AI/ML, Free, Web Dev"
              />
            </Field>
          </div>

          <Field label="Notes">
            <Textarea
              value={form.notes}
              onChange={e => update('notes', e.target.value)}
              placeholder="Application details, contacts, next steps..."
              rows={2}
              className="resize-none"
            />
          </Field>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="ghost"
              onClick={onCancel}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={submitting} aria-busy={submitting}>
              {submitting ? 'Saving…' : isEdit ? 'Update' : 'Add opportunity'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function Field({
  label,
  required,
  error,
  hint,
  children,
}: {
  label: string;
  required?: boolean;
  error?: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-ink-soft">
        {label}
        {required && (
          <span className="text-critical" aria-hidden="true">
            *
          </span>
        )}
        {hint && (
          <span className="font-mono text-[11px] text-ink-faint">({hint})</span>
        )}
      </Label>
      {children}
      {error && (
        <p className="text-xs text-critical" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
