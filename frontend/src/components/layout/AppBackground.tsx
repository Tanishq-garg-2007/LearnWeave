import React from "react";
import { cn } from "@/lib/cn";

export interface AppBackgroundProps {
  variant?: "default" | "wave";
  className?: string;
}

export function AppBackground({ variant = "wave", className }: AppBackgroundProps): JSX.Element {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "absolute inset-0 pointer-events-none -z-10 overflow-hidden select-none",
        className
      )}
    >
      {/* Saturated continuous pastel mesh gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#CFE5FE] via-[#EAE2FD] to-[#FEDBC7]" />

      {/* Atmospheric ambient glows with rich saturation */}
      {/* Top Left: Icy Cyan & Electric Sky */}
      <div className="absolute -top-24 -left-24 h-[620px] w-[620px] rounded-full bg-[#38BDF8]/40 blur-[130px] motion-safe:animate-pulse motion-safe:duration-[10000ms]" />

      {/* Top Center-Right: Vivid Lavender & Iris */}
      <div className="absolute -top-20 right-1/4 h-[550px] w-[550px] rounded-full bg-[#A78BFA]/38 blur-[120px]" />

      {/* Mid Right: Rose Blush & Coral */}
      <div className="absolute top-1/3 -right-20 h-[620px] w-[620px] rounded-full bg-[#FB7185]/35 blur-[140px]" />

      {/* Center & Bottom: Warm Melon Peach & Honey Apricot */}
      <div className="absolute bottom-1/5 left-1/4 h-[680px] w-[680px] rounded-full bg-[#FB923C]/32 blur-[150px]" />
      <div className="absolute -bottom-32 right-1/5 h-[700px] w-[700px] rounded-full bg-[#F472B6]/30 blur-[140px]" />

      {/* Tactile precision grid overlay with luminous cyan lines matching reference */}
      <div
        className="absolute inset-0 opacity-[0.22]"
        style={{
          backgroundImage:
            "linear-gradient(to right, rgba(56, 189, 248, 0.35) 1px, transparent 1px), linear-gradient(to bottom, rgba(56, 189, 248, 0.35) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />

      {/* Flowing layered 3D wave ribbons with saturated coral, peach, lavender, and cyan highlights */}
      {variant === "wave" && (
        <div className="absolute bottom-0 left-0 right-0 h-64 sm:h-80 md:h-[400px] pointer-events-none overflow-hidden">
          <svg
            className="w-full h-full object-cover"
            viewBox="0 0 1440 380"
            fill="none"
            preserveAspectRatio="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <defs>
              <linearGradient id="wave-lavender" x1="0%" y1="20%" x2="100%" y2="80%">
                <stop offset="0%" stopColor="#93C5FD" stopOpacity="0.55" />
                <stop offset="50%" stopColor="#C4B5FD" stopOpacity="0.7" />
                <stop offset="100%" stopColor="#FDA4AF" stopOpacity="0.65" />
              </linearGradient>

              <linearGradient id="wave-coral" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#FB923C" stopOpacity="0.75" />
                <stop offset="35%" stopColor="#F87171" stopOpacity="0.82" />
                <stop offset="70%" stopColor="#F472B6" stopOpacity="0.78" />
                <stop offset="100%" stopColor="#60A5FA" stopOpacity="0.65" />
              </linearGradient>

              <linearGradient id="wave-foreground" x1="0%" y1="50%" x2="100%" y2="50%">
                <stop offset="0%" stopColor="#EA580C" stopOpacity="0.8" />
                <stop offset="25%" stopColor="#F43F5E" stopOpacity="0.88" />
                <stop offset="55%" stopColor="#FB7185" stopOpacity="0.85" />
                <stop offset="85%" stopColor="#38BDF8" stopOpacity="0.9" />
                <stop offset="100%" stopColor="#0284C7" stopOpacity="0.8" />
              </linearGradient>

              <linearGradient id="wave-crest" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#0284C7" stopOpacity="0.9" />
                <stop offset="40%" stopColor="#F43F5E" stopOpacity="0.95" />
                <stop offset="75%" stopColor="#6366F1" stopOpacity="1" />
                <stop offset="100%" stopColor="#0EA5E9" stopOpacity="0.9" />
              </linearGradient>
            </defs>

            {/* Layer 1: Soft deep back swell */}
            <path
              d="M0,210 C240,140 480,270 720,190 C960,120 1200,240 1440,170 L1440,380 L0,380 Z"
              fill="url(#wave-lavender)"
            />

            {/* Layer 2: Main flowing coral & peach ribbon */}
            <path
              d="M0,250 C280,180 520,310 800,210 C1080,120 1280,260 1440,190 L1440,380 L0,380 Z"
              fill="url(#wave-coral)"
            />

            {/* Layer 3: Foreground sculpted dynamic wave */}
            <path
              d="M0,290 C200,240 420,320 680,240 C940,160 1180,280 1440,230 L1440,380 L0,380 Z"
              fill="url(#wave-foreground)"
            />

            {/* Layer 4: Thin illuminated wave crest curve */}
            <path
              d="M0,290 C200,240 420,320 680,240 C940,160 1180,280 1440,230"
              stroke="url(#wave-crest)"
              strokeWidth="3"
              fill="none"
              strokeLinecap="round"
            />

            {/* Secondary delicate specular stroke */}
            <path
              d="M0,250 C280,180 520,310 800,210 C1080,120 1280,260 1440,190"
              stroke="#FFFFFF"
              strokeOpacity="0.65"
              strokeWidth="1.8"
              fill="none"
            />
          </svg>
        </div>
      )}
    </div>
  );
}

export default AppBackground;
