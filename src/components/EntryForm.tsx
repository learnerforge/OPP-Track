import { useState, useEffect, useRef, useCallback } from 'react';
import type { Opportunity } from '../types/opportunity';
import { TYPE_OPTIONS, STATUS_OPTIONS } from '../constants';
import { validateOpportunity, getFieldError } from '../utils';

interface EntryFormProps {
  onSave: (opp: Opportunity) => void;
  onCancel: () => void;
  initial?: Opportunity;
  isEdit?: boolean;
}

export function EntryForm({ onSave, onCancel, initial, isEdit = false }: EntryFormProps) {
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
    ...(initial
      ? {
          ...initial,
          tags: initial.tags.join(', '),
        }
      : {}),
  });
  const [errors, setErrors] = useState<{ field: string; message: string }[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const titleRef = useRef<HTMLInputElement>(null);
  const formRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    titleRef.current?.focus();
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        onCancel();
      }
    },
    [onCancel]
  );

  function update(field: keyof typeof form, value: string) {
    setForm(prev => ({ ...prev, [field]: value }));
    setErrors(prev => prev.filter(e => e.field !== field));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const oppData: Partial<Opportunity> = {
      ...form,
      tags: form.tags
        .split(',')
        .map(t => t.trim())
        .filter(Boolean),
    };

    const validationErrors = validateOpportunity(oppData, isEdit);
    if (validationErrors.length > 0) {
      setErrors(validationErrors);
      const firstErrorField = formRef.current?.querySelector<HTMLElement>(
        `[data-field="${validationErrors[0].field}"]`
      );
      firstErrorField?.focus();
      return;
    }

    setSubmitting(true);
    try {
      const entry: Opportunity = {
        id: isEdit && initial ? initial.id : '',
        title: form.title.trim(),
        type: form.type,
        source: form.source.trim(),
        link: form.link.trim(),
        deadline: form.deadline,
        eligibility: form.eligibility.trim(),
        tags: form.tags
          .split(',')
          .map(t => t.trim())
          .filter(Boolean),
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
    <div
      ref={formRef}
      role="dialog"
      aria-modal="true"
      aria-label={isEdit ? 'Edit opportunity' : 'Add new opportunity'}
      onKeyDown={handleKeyDown}
      className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 animate-slide-in"
    >
      <h3 className="text-lg font-semibold text-gray-800 mb-4">
        {isEdit ? 'Edit Opportunity' : 'Add New Opportunity'}
      </h3>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Title" required error={getFieldError(errors, 'title')}>
          <input
            ref={titleRef}
            type="text"
            value={form.title}
            onChange={e => update('title', e.target.value)}
            placeholder="e.g. Smart India Hackathon 2026"
            className={inputClass(getFieldError(errors, 'title'))}
            data-field="title"
            aria-required="true"
            aria-invalid={!!getFieldError(errors, 'title')}
          />
        </Field>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Type" required error={getFieldError(errors, 'type')}>
            <select
              value={form.type}
              onChange={e => update('type', e.target.value)}
              className={inputClass()}
              data-field="type"
              aria-required="true"
            >
              {TYPE_OPTIONS.map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </Field>
          <Field label="Status">
            <select
              value={form.status}
              onChange={e => update('status', e.target.value)}
              className={inputClass()}
              aria-label="Status"
            >
              {STATUS_OPTIONS.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </Field>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Source Platform">
            <input
              type="text"
              value={form.source}
              onChange={e => update('source', e.target.value)}
              placeholder="e.g. Unstop, Internshala"
              className={inputClass()}
            />
          </Field>
          <Field
            label="Deadline"
            required
            error={getFieldError(errors, 'deadline')}
            hint="IST"
          >
            <input
              type="date"
              value={form.deadline}
              onChange={e => update('deadline', e.target.value)}
              className={inputClass(getFieldError(errors, 'deadline'))}
              data-field="deadline"
              aria-required="true"
              aria-invalid={!!getFieldError(errors, 'deadline')}
            />
          </Field>
        </div>

        <Field label="Link" error={getFieldError(errors, 'link')}>
          <input
            type="url"
            value={form.link}
            onChange={e => update('link', e.target.value)}
            placeholder="https://..."
            className={inputClass(getFieldError(errors, 'link'))}
            data-field="link"
            aria-invalid={!!getFieldError(errors, 'link')}
          />
        </Field>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Eligibility">
            <input
              type="text"
              value={form.eligibility}
              onChange={e => update('eligibility', e.target.value)}
              placeholder="e.g. 3rd year, teams of 4"
              className={inputClass()}
            />
          </Field>
          <Field label="Tags" hint="comma-separated">
            <input
              type="text"
              value={form.tags}
              onChange={e => update('tags', e.target.value)}
              placeholder="AI/ML, Free, Web Dev"
              className={inputClass()}
            />
          </Field>
        </div>

        <Field label="Notes">
          <textarea
            value={form.notes}
            onChange={e => update('notes', e.target.value)}
            placeholder="Application details, contacts, next steps..."
            rows={2}
            className={`${inputClass()} resize-none`}
          />
        </Field>

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={submitting}
            aria-busy={submitting}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white font-medium px-5 py-2.5 rounded-lg text-sm transition-colors min-w-[120px]"
          >
            {submitting ? 'Saving...' : isEdit ? 'Update' : 'Add Opportunity'}
          </button>
          <button
            type="button"
            onClick={onCancel}
            disabled={submitting}
            className="bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium px-5 py-2.5 rounded-lg text-sm transition-colors"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
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
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}
        {required && <span className="text-red-500 ml-0.5" aria-hidden="true">*</span>}
        {hint && <span className="text-gray-400 font-normal ml-1">({hint})</span>}
      </label>
      {children}
      {error && (
        <p className="text-red-500 text-xs mt-1" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

function inputClass(error?: string): string {
  const base = 'w-full px-3 py-2 border rounded-lg text-sm';
  const focus = 'focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500';
  if (error) return `${base} border-red-400 bg-red-50 ${focus}`;
  return `${base} border-gray-300 ${focus}`;
}
