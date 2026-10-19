import React from "react";
import { cn } from "@/lib/cn";

export interface SliderProps {
  id?: string;
  min?: number;
  max?: number;
  step?: number;
  value: number;
  onChange: (value: number) => void;
  label?: string;
  formatValue?: (val: number) => string;
  disabled?: boolean;
  className?: string;
}

export function Slider({
  id,
  min = 0,
  max = 100,
  step = 1,
  value,
  onChange,
  label,
  formatValue = (v) => String(v),
  disabled = false,
  className,
}: SliderProps): JSX.Element {
  const generatedId = React.useId();
  const inputId = id || generatedId;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(Number(e.target.value));
  };

  const percentage = Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100));

  return (
    <div className={cn("w-full space-y-1.5", className)}>
      <div className="flex items-center justify-between text-xs font-medium text-text select-none">
        {label && <label htmlFor={inputId}>{label}</label>}
        <span className="font-mono text-muted">{formatValue(value)}</span>
      </div>
      <div className="relative flex items-center h-6">
        <input
          id={inputId}
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          disabled={disabled}
          onChange={handleChange}
          aria-valuemin={min}
          aria-valuemax={max}
          aria-valuenow={value}
          className={cn(
            "w-full h-2 bg-black/10 rounded-lg appearance-none cursor-pointer",
            "accent-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            "slider-range"
          )}
          style={{
            background: `linear-gradient(to right, rgb(var(--ink)) 0%, rgb(var(--ink)) ${percentage}%, rgba(var(--ink) / 0.12) ${percentage}%, rgba(var(--ink) / 0.12) 100%)`,
          }}
        />
      </div>
    </div>
  );
}

export default Slider;
