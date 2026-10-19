import React from "react";
import { cn } from "@/lib/cn";
import { Spinner } from "./Spinner";
import { ButtonVariant, ButtonSize } from "./Button";

export interface IconButtonProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "aria-label"> {
  "aria-label": string; // Explicitly required for accessibility
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  children: React.ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary: "bg-ink text-white hover:bg-ink/90 active:scale-[0.98] shadow-sm",
  secondary: "bg-white/80 text-ink border border-surface-border hover:bg-white active:scale-[0.98] shadow-sm",
  ghost: "bg-transparent text-ink hover:bg-ink/5 active:bg-ink/10",
  danger: "bg-danger text-white hover:bg-danger/90 active:scale-[0.98] shadow-sm",
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: "h-8 w-8 text-xs p-1.5 rounded-full",
  md: "h-10 w-10 text-sm p-2 rounded-full",
  lg: "h-12 w-12 text-base p-3 rounded-full",
};

export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  (
    {
      "aria-label": ariaLabel,
      variant = "ghost",
      size = "md",
      loading = false,
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
        aria-label={ariaLabel}
        disabled={isDisabled}
        className={cn(
          "inline-flex items-center justify-center shrink-0 transition-all select-none",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2",
          "disabled:opacity-60 disabled:cursor-not-allowed disabled:pointer-events-none",
          variantStyles[variant],
          sizeStyles[size],
          className
        )}
        {...props}
      >
        {loading ? (
          <Spinner size={size === "lg" ? "md" : "sm"} className="text-current" />
        ) : (
          children
        )}
      </button>
    );
  }
);

IconButton.displayName = "IconButton";

export default IconButton;
