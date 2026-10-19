import React from "react";
import { cn } from "@/lib/cn";

export interface AppBackgroundProps {
  variant?: "default" | "wave";
  className?: string;
}

export function AppBackground({ variant = "default", className }: AppBackgroundProps): JSX.Element {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "fixed inset-0 pointer-events-none -z-10 overflow-hidden select-none",
        className
      )}
    >
      {/* Base gradient layer */}
      <div className="absolute inset-0 bg-gradient-to-b from-white/40 via-cream/30 to-cream/60" />

      {/* Atmospheric gradient glows */}
      {/* Sky glow (top left) */}
      <div className="absolute -top-40 -left-40 h-[650px] w-[650px] rounded-full bg-sky/40 blur-[120px] motion-safe:animate-pulse motion-safe:duration-[10000ms]" />

      {/* Blush glow (top right) */}
      <div className="absolute -top-32 -right-32 h-[600px] w-[600px] rounded-full bg-blush/50 blur-[120px]" />

      {/* Lavender & cream glow (center to bottom) */}
      <div className="absolute top-1/3 left-1/4 h-[700px] w-[700px] rounded-full bg-lavender/35 blur-[140px]" />
      <div className="absolute -bottom-40 left-1/3 h-[750px] w-[750px] rounded-full bg-cream/70 blur-[130px]" />

      {/* Faint grid overlay at ~6% opacity */}
      <div
        className="absolute inset-0 opacity-[0.06]"
        style={{
          backgroundImage:
            "linear-gradient(to right, rgb(var(--ink)) 1px, transparent 1px), linear-gradient(to bottom, rgb(var(--ink)) 1px, transparent 1px)",
          backgroundSize: "44px 44px",
        }}
      />

      {/* Soft ribbon wave for landing / auth variants */}
      {variant === "wave" && (
        <div className="absolute bottom-0 left-0 right-0 h-64 md:h-96 opacity-60 overflow-hidden">
          <svg
            className="w-full h-full object-cover motion-safe:translate-y-0"
            viewBox="0 0 1440 320"
            fill="none"
            preserveAspectRatio="none"
          >
            <path
              d="M0,192L48,202.7C96,213,192,235,288,218.7C384,203,480,149,576,144C672,139,768,181,864,197.3C960,213,1056,203,1152,176C1248,149,1344,107,1392,85.3L1440,64L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"
              fill="url(#wave-gradient-1)"
              fillOpacity="0.4"
            />
            <path
              d="M0,256L60,240C120,224,240,192,360,192C480,192,600,224,720,240C840,256,960,256,1080,234.7C1200,213,1320,171,1380,149.3L1440,128L1440,320L1380,320C1320,320,1200,320,1080,320C960,320,840,320,720,320C600,320,480,320,360,320C240,320,120,320,60,320L0,320Z"
              fill="url(#wave-gradient-2)"
              fillOpacity="0.5"
            />
            <defs>
              <linearGradient id="wave-gradient-1" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#C4E1F9" />
                <stop offset="50%" stopColor="#FACECF" />
                <stop offset="100%" stopColor="#E9D7CD" />
              </linearGradient>
              <linearGradient id="wave-gradient-2" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#937EDD" stopOpacity="0.25" />
                <stop offset="50%" stopColor="#6EA2F6" stopOpacity="0.3" />
                <stop offset="100%" stopColor="#FACECF" stopOpacity="0.4" />
              </linearGradient>
            </defs>
          </svg>
        </div>
      )}
    </div>
  );
}

export default AppBackground;
