import React from "react";
import { cn } from "@/lib/cn";

export type AvatarSize = "sm" | "md" | "lg" | "xl";

export interface AvatarProps extends React.HTMLAttributes<HTMLDivElement> {
  name?: string;
  src?: string;
  size?: AvatarSize;
  className?: string;
}

const sizeStyles: Record<AvatarSize, { container: string; text: string }> = {
  sm: { container: "h-7 w-7", text: "text-xs" },
  md: { container: "h-9 w-9", text: "text-xs" },
  lg: { container: "h-11 w-11", text: "text-sm" },
  xl: { container: "h-14 w-14", text: "text-base" },
};

function getInitials(name?: string): string {
  if (!name) return "LW";
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function Avatar({
  name,
  src,
  size = "md",
  className,
  ...props
}: AvatarProps): JSX.Element {
  const [hasError, setHasError] = React.useState(false);
  const initials = getInitials(name);
  const { container, text } = sizeStyles[size];

  return (
    <div
      className={cn(
        "relative inline-flex items-center justify-center rounded-full overflow-hidden select-none shrink-0 font-medium",
        "bg-gradient-to-tr from-accent-from to-sky text-ink border border-white/60 shadow-sm",
        container,
        className
      )}
      {...props}
    >
      {src && !hasError ? (
        <img
          src={src}
          alt={name || "User avatar"}
          onError={() => setHasError(true)}
          className="h-full w-full object-cover"
        />
      ) : (
        <span className={cn("font-semibold tracking-wide text-ink", text)}>
          {initials}
        </span>
      )}
    </div>
  );
}

export default Avatar;
