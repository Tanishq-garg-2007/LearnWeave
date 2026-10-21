import React from "react";
import { cn } from "@/lib/cn";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, error, leftIcon, rightIcon, type = "text", disabled, ...props }, ref) => {
    return (
      <div className="relative w-full">
        {leftIcon && (
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-muted">
            {leftIcon}
          </div>
        )}
        <input
          ref={ref}
          type={type}
          disabled={disabled}
          aria-invalid={error ? true : undefined}
          className={cn(
            "w-full rounded-2xl bg-white/80 border border-surface-border text-sm text-text placeholder:text-muted/60 transition-all",
            "px-4 py-2.5",
            leftIcon ? "pl-10" : "",
            rightIcon ? "pr-10" : "",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:border-transparent",
            "disabled:opacity-60 disabled:cursor-not-allowed",
            error ? "border-danger focus-visible:ring-danger/50" : "",
            className
          )}
          {...props}
        />
        {rightIcon && (
          <div className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-muted">
            {rightIcon}
          </div>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";

export default Input;
