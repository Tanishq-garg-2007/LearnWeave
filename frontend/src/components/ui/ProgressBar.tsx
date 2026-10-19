import React from "react";
import { cn } from "@/lib/cn";

export interface ProgressBarProps {
  value: number;
  min?: number;
  max?: number;
  label?: string;
  showValue?: boolean;
  className?: string;
}

export function ProgressBar({
  value,
  min = 0,
  max = 100,
  label,
  showValue = false,
  className,
}: ProgressBarProps): JSX.Element {
  const percentage = Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100));

  return (
    <div className={cn("w-full space-y-1.5", className)}>
      {(label || showValue) && (
        <div className="flex items-center justify-between text-xs font-medium text-text select-none">
          {label && <span>{label}</span>}
          {showValue && <span className="font-mono text-muted">{Math.round(percentage)}%</span>}
        </div>
      )}
      <div
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-label={label || "Progress"}
        className="h-2.5 w-full overflow-hidden rounded-full bg-black/10 relative"
      >
        <div
          className="h-full rounded-full bg-gradient-to-r from-accent-from to-accent-to transition-all duration-500 ease-out"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

export default ProgressBar;
