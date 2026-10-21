import React from "react";
import { cn } from "@/lib/cn";

export interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children?: React.ReactNode;
  padding?: "none" | "sm" | "md" | "lg";
  variant?: "default" | "sky" | "peach" | "lavender" | "mint";
  className?: string;
  as?: React.ElementType;
}

const paddingStyles: Record<NonNullable<GlassCardProps["padding"]>, string> = {
  none: "p-0",
  sm: "p-4 sm:p-5",
  md: "p-6 sm:p-8",
  lg: "p-8 sm:p-12",
};

const variantStyles: Record<NonNullable<GlassCardProps["variant"]>, string> = {
  default:
    "bg-white/55 border-white/85 shadow-[0_16px_40px_-10px_rgba(40,30,60,0.08)] ring-1 ring-inset ring-white/80",
  sky:
    "bg-[#E0F2FE]/45 border-[#BAE6FD]/85 shadow-[0_16px_40px_-10px_rgba(14,165,233,0.14)] ring-1 ring-inset ring-white/80",
  peach:
    "bg-[#FFEDD5]/45 border-[#FED7AA]/85 shadow-[0_16px_40px_-10px_rgba(249,115,22,0.12)] ring-1 ring-inset ring-white/80",
  lavender:
    "bg-[#EDE9FE]/45 border-[#DDD6FE]/85 shadow-[0_16px_40px_-10px_rgba(139,92,246,0.12)] ring-1 ring-inset ring-white/80",
  mint:
    "bg-[#ECFDF5]/45 border-[#A7F3D0]/85 shadow-[0_16px_40px_-10px_rgba(16,185,129,0.12)] ring-1 ring-inset ring-white/80",
};

export const GlassCard = React.forwardRef<HTMLDivElement, GlassCardProps>(
  (
    {
      children,
      padding = "md",
      variant = "default",
      className,
      as: Component = "div",
      ...props
    },
    ref
  ) => {
    return (
      <Component
        ref={ref}
        className={cn(
          "rounded-3xl backdrop-blur-2xl glass-surface transition-all duration-200 border",
          variantStyles[variant],
          paddingStyles[padding],
          className
        )}
        {...props}
      >
        {children}
      </Component>
    );
  }
);

GlassCard.displayName = "GlassCard";

export default GlassCard;
