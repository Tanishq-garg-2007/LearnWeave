import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/cn";
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from "lucide-react";
import { IconButton } from "./IconButton";

export type ToastType = "success" | "error" | "info" | "warning";

export interface ToastAction {
  label: string;
  onClick: () => void;
}

export interface ToastOptions {
  title: string;
  description?: string;
  action?: ToastAction;
  duration?: number;
}

export interface ToastItem extends ToastOptions {
  id: string;
  type: ToastType;
}

interface ToastContextType {
  toast: (type: ToastType, options: ToastOptions) => void;
  success: (title: string, options?: Omit<ToastOptions, "title">) => void;
  error: (title: string, options?: Omit<ToastOptions, "title">) => void;
  info: (title: string, options?: Omit<ToastOptions, "title">) => void;
  warning: (title: string, options?: Omit<ToastOptions, "title">) => void;
  dismiss: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | null>(null);

const MAX_TOASTS = 3;

interface SingleToastProps {
  toast: ToastItem;
  onDismiss: (id: string) => void;
}

function SingleToast({ toast, onDismiss }: SingleToastProps): JSX.Element {
  const isError = toast.type === "error";
  const defaultDuration = isError ? 6000 : 4000;
  const duration = toast.duration ?? defaultDuration;

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const startTimeRef = useRef<number>(Date.now());
  const remainingRef = useRef<number>(duration);
  const isPausedRef = useRef<boolean>(false);

  const startTimer = useCallback(() => {
    isPausedRef.current = false;
    startTimeRef.current = Date.now();
    timerRef.current = setTimeout(() => {
      onDismiss(toast.id);
    }, remainingRef.current);
  }, [toast.id, onDismiss]);

  const pauseTimer = useCallback(() => {
    if (timerRef.current && !isPausedRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
      const elapsed = Date.now() - startTimeRef.current;
      remainingRef.current = Math.max(0, remainingRef.current - elapsed);
      isPausedRef.current = true;
    }
  }, []);

  useEffect(() => {
    startTimer();
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [startTimer]);

  const icons: Record<ToastType, JSX.Element> = {
    success: <CheckCircle2 className="w-5 h-5 text-green-600 shrink-0" />,
    error: <AlertCircle className="w-5 h-5 text-red-600 shrink-0" />,
    warning: <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />,
    info: <Info className="w-5 h-5 text-sky-600 shrink-0" />,
  };

  return (
    <div
      role={isError ? "alert" : "status"}
      onMouseEnter={pauseTimer}
      onMouseLeave={startTimer}
      onFocus={pauseTimer}
      onBlur={startTimer}
      tabIndex={0}
      className={cn(
        "pointer-events-auto flex items-start gap-3 p-4 rounded-2xl bg-white/95 border border-white/80 shadow-glass",
        "backdrop-blur-xl text-sm transition-all duration-300 w-full",
        "motion-safe:animate-in motion-safe:slide-in-from-top-4 motion-safe:fade-in",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
      )}
    >
      <div className="pt-0.5">{icons[toast.type]}</div>
      <div className="flex-1 min-w-0">
        <h4 className="font-semibold text-text text-sm leading-snug">{toast.title}</h4>
        {toast.description && (
          <p className="text-muted text-xs mt-0.5 leading-relaxed">{toast.description}</p>
        )}
        {toast.action && (
          <button
            type="button"
            onClick={toast.action.onClick}
            className="mt-2 text-xs font-semibold text-ink underline hover:opacity-80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          >
            {toast.action.label}
          </button>
        )}
      </div>
      <IconButton
        aria-label="Dismiss notification"
        variant="ghost"
        size="sm"
        onClick={() => onDismiss(toast.id)}
        className="-mr-1 -mt-1 text-muted hover:text-text h-7 w-7"
      >
        <X className="w-3.5 h-3.5" />
      </IconButton>
    </div>
  );
}

export function ToastProvider({ children }: { children: React.ReactNode }): JSX.Element {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback((type: ToastType, options: ToastOptions) => {
    const id = Math.random().toString(36).slice(2, 9);
    const newToast: ToastItem = { ...options, id, type };
    setToasts((prev) => [...prev.slice(-(MAX_TOASTS - 1)), newToast]);
  }, []);

  const success = useCallback(
    (title: string, options?: Omit<ToastOptions, "title">) => toast("success", { ...options, title }),
    [toast]
  );
  const error = useCallback(
    (title: string, options?: Omit<ToastOptions, "title">) => toast("error", { ...options, title }),
    [toast]
  );
  const info = useCallback(
    (title: string, options?: Omit<ToastOptions, "title">) => toast("info", { ...options, title }),
    [toast]
  );
  const warning = useCallback(
    (title: string, options?: Omit<ToastOptions, "title">) => toast("warning", { ...options, title }),
    [toast]
  );

  return (
    <ToastContext.Provider value={{ toast, success, error, info, warning, dismiss }}>
      {children}
      {mounted &&
        createPortal(
          <div
            aria-live="polite"
            className="fixed top-4 left-1/2 -translate-x-1/2 md:translate-x-0 md:left-auto md:right-4 z-50 flex flex-col gap-2.5 max-w-sm w-[calc(100vw-2rem)] md:w-96 pt-[env(safe-area-inset-top,0px)] pointer-events-none"
          >
            {toasts.map((t) => (
              <SingleToast key={t.id} toast={t} onDismiss={dismiss} />
            ))}
          </div>,
          document.body
        )}
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextType {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}

export default ToastProvider;
