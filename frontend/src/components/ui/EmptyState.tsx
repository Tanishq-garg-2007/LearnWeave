import React from "react";
import { cn } from "@/lib/cn";

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps): JSX.Element {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center p-8 sm:p-12 rounded-3xl",
        "bg-white/40 border border-white/60 shadow-soft",
        className
      )}
    >
      {icon && (
        <div className="mb-4 p-4 rounded-2xl bg-gradient-to-tr from-sky/30 to-blush/30 text-ink shadow-sm">
          {icon}
        </div>
      )}
      <h3 className="text-base font-semibold text-text tracking-tight mb-1.5 font-sans">
        {title}
      </h3>
      {description && (
        <p className="text-sm text-muted max-w-sm mb-6 leading-relaxed">
          {description}
        </p>
      )}
      {action && <div className="inline-flex items-center gap-3">{action}</div>}
    </div>
  );
}

export default EmptyState;
