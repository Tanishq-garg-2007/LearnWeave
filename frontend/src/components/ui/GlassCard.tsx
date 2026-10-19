import React from "react";
import { cn } from "@/lib/cn";

export interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children?: React.ReactNode;
  padding?: "none" | "sm" | "md" | "lg";
  className?: string;
  as?: React.ElementType;
}

const paddingStyles: Record<NonNullable<GlassCardProps["padding"]>, string> = {
  none: "p-0",
  sm: "p-4 sm:p-5",
  md: "p-6 sm:p-8",
  lg: "p-8 sm:p-12",
};

export const GlassCard = React.forwardRef<HTMLDivElement, GlassCardProps>(
  ({ children, padding = "md", className, as: Component = "div", ...props }, ref) => {
    return (
      <Component
        ref={ref}
        className={cn(
          "bg-white/60 border border-white/70 shadow-glass rounded-3xl backdrop-blur-md md:backdrop-blur-xl glass-surface transition-all duration-200",
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
