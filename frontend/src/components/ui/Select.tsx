import React from "react";
import { cn } from "@/lib/cn";
import { ChevronDown } from "lucide-react";

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  error?: boolean;
  options?: SelectOption[];
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, error, disabled, options, children, ...props }, ref) => {
    return (
      <div className="relative w-full">
        <select
          ref={ref}
          disabled={disabled}
          aria-invalid={error ? true : undefined}
          className={cn(
            "w-full appearance-none rounded-2xl bg-white/80 border border-surface-border text-sm text-text transition-all",
            "px-4 py-2.5 pr-10",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:border-transparent",
            "disabled:opacity-60 disabled:cursor-not-allowed",
            error ? "border-danger focus-visible:ring-danger/50" : "",
            className
          )}
          {...props}
        >
          {options
            ? options.map((opt) => (
                <option key={opt.value} value={opt.value} disabled={opt.disabled}>
                  {opt.label}
                </option>
              ))
            : children}
        </select>
        <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3.5 text-muted">
          <ChevronDown className="h-4 w-4" aria-hidden="true" />
        </div>
      </div>
    );
  }
);

Select.displayName = "Select";

export default Select;
