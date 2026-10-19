import React from "react";
import { cn } from "@/lib/cn";

export type BadgeVariant = "neutral" | "info" | "success" | "warning" | "accent" | "danger";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  children: React.ReactNode;
}

const variantStyles: Record<BadgeVariant, string> = {
  neutral: "bg-black/5 text-text border border-black/10",
  info: "bg-sky/40 text-blue-900 border border-blue-200/60",
  success: "bg-green-100 text-green-900 border border-green-300/60",
  warning: "bg-amber-100 text-amber-900 border border-amber-300/60",
  accent: "bg-accent-from/15 text-indigo-950 border border-accent-from/30",
  danger: "bg-red-100 text-red-900 border border-red-300/60",
};

export function Badge({
  variant = "neutral",
  className,
  children,
  ...props
}: BadgeProps): JSX.Element {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide select-none",
        variantStyles[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}

export default Badge;
