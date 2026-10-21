import React, { useEffect, useRef, useId } from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/cn";
import { IconButton } from "./IconButton";
import { X } from "lucide-react";

export type ModalSize = "sm" | "md" | "lg";

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  size?: ModalSize;
  dismissible?: boolean;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

const sizeStyles: Record<ModalSize, string> = {
  sm: "max-w-md",
  md: "max-w-xl",
  lg: "max-w-3xl",
};

export function Modal({
  open,
  onClose,
  title,
  description,
  size = "md",
  dismissible = true,
  children,
  footer,
  className,
}: ModalProps): JSX.Element | null {
  const [mounted, setMounted] = React.useState(false);
  const modalRef = useRef<HTMLDivElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);
  const titleId = useId();
  const descId = useId();

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!open) return;

    // Store element focused before modal opened
    previousActiveElement.current = document.activeElement as HTMLElement | null;

    // Lock body scroll
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    // Focus first focusable element
    const timeout = setTimeout(() => {
      if (modalRef.current) {
        const focusables = modalRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (focusables.length > 0) {
          focusables[0].focus();
        } else {
          modalRef.current.focus();
        }
      }
    }, 50);

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && dismissible) {
        e.preventDefault();
        onClose();
        return;
      }

      if (e.key === "Tab" && modalRef.current) {
        const focusableElements = Array.from(
          modalRef.current.querySelectorAll<HTMLElement>(
            'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
          )
        ).filter((el) => el.offsetParent !== null);

        if (focusableElements.length === 0) return;

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
          }
        } else {
          if (document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
          }
        }
      }
    };

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      clearTimeout(timeout);
      document.body.style.overflow = previousOverflow;
      if (previousActiveElement.current && typeof previousActiveElement.current.focus === "function") {
        previousActiveElement.current.focus();
      }
    };
  }, [open, dismissible, onClose]);

  if (!mounted || !open) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-ink/40 backdrop-blur-sm transition-opacity motion-safe:duration-200"
        aria-hidden="true"
        onClick={() => {
          if (dismissible) onClose();
        }}
      />

      {/* Modal Dialog Surface */}
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descId : undefined}
        tabIndex={-1}
        className={cn(
          "relative w-full z-10 bg-white/95 border border-white/80 shadow-glass rounded-3xl p-6 sm:p-8",
          "backdrop-blur-xl transition-all duration-200",
          "motion-safe:animate-in motion-safe:fade-in motion-safe:zoom-in-95",
          "focus:outline-none",
          sizeStyles[size],
          className
        )}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h2 id={titleId} className="text-xl font-bold font-sans text-text tracking-tight">
              {title}
            </h2>
            {description && (
              <p id={descId} className="text-sm text-muted mt-1 leading-relaxed">
                {description}
              </p>
            )}
          </div>
          {dismissible && (
            <IconButton
              aria-label="Close dialog"
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="-mr-1 -mt-1 text-muted hover:text-text"
            >
              <X className="h-4 w-4" />
            </IconButton>
          )}
        </div>

        {/* Content Body */}
        <div className="text-text text-sm leading-relaxed">{children}</div>

        {/* Footer */}
        {footer && (
          <div className="mt-6 pt-4 border-t border-surface-border flex items-center justify-end gap-3">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body
  );
}

export default Modal;
