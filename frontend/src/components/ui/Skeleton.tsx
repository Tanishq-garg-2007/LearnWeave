import React from "react";
import { cn } from "@/lib/cn";

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  className?: string;
  circle?: boolean;
}

export function Skeleton({
  className,
  circle = false,
  ...props
}: SkeletonProps): JSX.Element {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "animate-pulse bg-black/10 select-none",
        circle ? "rounded-full" : "rounded-2xl",
        className
      )}
      {...props}
    />
  );
}

export default Skeleton;
