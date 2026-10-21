import React from "react";
import { cn } from "@/lib/cn";
import { Spinner } from "./Spinner";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  fullWidth?: boolean;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary: "bg-ink text-white hover:bg-ink/90 active:scale-[0.98] shadow-sm",
  secondary: "bg-white/80 text-ink border border-surface-border hover:bg-white active:scale-[0.98] shadow-sm",
  ghost: "bg-transparent text-ink hover:bg-ink/5 active:bg-ink/10",
  danger: "bg-danger text-white hover:bg-danger/90 active:scale-[0.98] shadow-sm",
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: "text-xs px-3.5 py-1.5 gap-1.5 font-medium rounded-full",
  md: "text-sm px-5 py-2.5 gap-2 font-medium rounded-full",
  lg: "text-base px-6 py-3.5 gap-2.5 font-semibold rounded-full",
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      loading = false,
      leftIcon,
      rightIcon,
      fullWidth = false,
      disabled,
      className,
      children,
      type = "button",
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        type={type}
        disabled={isDisabled}
        className={cn(
          "inline-flex items-center justify-center transition-all select-none",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2",
          "disabled:opacity-60 disabled:cursor-not-allowed disabled:pointer-events-none",
          variantStyles[variant],
          sizeStyles[size],
          fullWidth ? "w-full" : "",
          className
        )}
        {...props}
      >
        {loading ? (
          <Spinner size={size === "lg" ? "md" : "sm"} className="text-current" />
        ) : (
          leftIcon && <span className="inline-flex shrink-0">{leftIcon}</span>
        )}
        <span>{children}</span>
        {!loading && rightIcon && (
          <span className="inline-flex shrink-0">{rightIcon}</span>
        )}
      </button>
    );
  }
);

Button.displayName = "Button";

export default Button;
