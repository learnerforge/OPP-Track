import {
  useState,
  useEffect,
  useCallback,
  createContext,
  useContext,
  useRef,
} from 'react';

export type ToastType = 'success' | 'error' | 'info';

interface Toast {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  showToast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}

let toastId = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timers = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());

  const removeToast = useCallback((id: number) => {
    timers.current.delete(id);
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const showToast = useCallback(
    (message: string, type: ToastType = 'success') => {
      const id = ++toastId;
      setToasts(prev => [...prev, { id, message, type }]);
      const timer = setTimeout(() => removeToast(id), 3000);
      timers.current.set(id, timer);
    },
    [removeToast]
  );

  useEffect(() => {
    return () => {
      timers.current.forEach(t => clearTimeout(t));
    };
  }, []);

  const typeMeta: Record<ToastType, { dot: string; label: string }> = {
    success: { dot: 'bg-safe', label: 'saved' },
    error: { dot: 'bg-critical', label: 'error' },
    info: { dot: 'bg-accent', label: 'note' },
  };

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div
        aria-live="polite"
        aria-label="Notifications"
        className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2"
      >
        {toasts.map(toast => {
          const meta = typeMeta[toast.type];
          return (
            <div
              key={toast.id}
              role="status"
              className="animate-slide-in pointer-events-auto flex items-start gap-2.5 rounded-lg border border-rule bg-surface px-4 py-3 shadow-lg"
            >
              <span
                className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${meta.dot}`}
                aria-hidden="true"
              />
              <div>
                <p className="kicker mb-0.5">{meta.label}</p>
                <p className="text-sm text-ink">{toast.message}</p>
              </div>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
