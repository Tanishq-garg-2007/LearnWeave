import React from "react";
import { cn } from "@/lib/cn";

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, error, disabled, rows = 3, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        rows={rows}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        className={cn(
          "w-full rounded-2xl bg-white/80 border border-surface-border text-sm text-text placeholder:text-muted/60 transition-all",
          "px-4 py-3",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:border-transparent",
          "disabled:opacity-60 disabled:cursor-not-allowed resize-y",
          error ? "border-danger focus-visible:ring-danger/50" : "",
          className
        )}
        {...props}
      />
    );
  }
);

Textarea.displayName = "Textarea";

export default Textarea;
