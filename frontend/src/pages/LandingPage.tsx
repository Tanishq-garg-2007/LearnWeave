import React from "react";
import { Link } from "react-router-dom";
import { GlassCard } from "@/components/ui/GlassCard";
import { Badge } from "@/components/ui/Badge";
import {
  ArrowRight,
  Sparkles,
  Bot,
  BrainCircuit,
  Compass,
  CheckCircle2,
  FileText,
  Target,
  Layers,
  Radio,
  Star,
  Clock,
  MessageSquare,
  Users,
  ShieldCheck,
} from "lucide-react";

export default function LandingPage(): JSX.Element {
  return (
    <div className="relative overflow-hidden py-8 sm:py-14 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-20 md:space-y-28">
      {/* Hero Section replicating reference composition */}
      <section
        aria-labelledby="hero-title"
        className="relative grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-6 items-center min-h-[580px]"
      >
        {/* Left Column: Headlines & Action Buttons */}
        <div className="lg:col-span-5 space-y-6 text-left relative z-20">
          <div className="inline-flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-white/80 border border-white/90 text-ink shadow-sm backdrop-blur-md">
              <Sparkles className="w-3.5 h-3.5 text-cyan-500" />
              Agentic Learning Network
            </span>
          </div>

          <h1
            id="hero-title"
            className="text-4xl sm:text-5xl lg:text-[3.5rem] font-display text-ink tracking-tight font-normal leading-[1.12]"
          >
            Collaborative Learning Powered by AI Agent Networks
          </h1>

          <p className="text-base sm:text-lg text-muted max-w-xl leading-relaxed">
            Learn with specialized AI tutors that collaborate, guide, and adapt to your career goals.
            Grounded directly in your uploaded notes and course materials.
          </p>

          <div className="flex flex-wrap items-center gap-3.5 pt-2">
            <Link to="/register">
              <button
                type="button"
                className="inline-flex items-center justify-center gap-2 px-7 py-3 rounded-full bg-[#252229] hover:bg-[#151318] text-white text-sm font-semibold shadow-lg shadow-black/10 transition-all active:scale-95 group"
              >
                <span>Start Your Journey</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
              </button>
            </Link>
            <Link to="/roadmap">
              <button
                type="button"
                className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-full bg-white/70 hover:bg-white text-ink border border-white/90 text-sm font-semibold shadow-sm backdrop-blur-md transition-all active:scale-95"
              >
                Explore Agents
              </button>
            </Link>
          </div>

          {/* Quick Features Row */}
          <div className="flex items-center gap-6 pt-4 text-xs font-medium text-muted">
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>RAG Note Grounding</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>6-Step Adaptive Cycle</span>
            </div>
          </div>
        </div>

        {/* Right Column: Reference-Inspired Visual Agent Network & Cards */}
        <div className="lg:col-span-7 relative w-full h-[540px] sm:h-[580px] select-none">
          {/* Cyan Dotted Connector Lines */}
          <svg
            className="absolute inset-0 w-full h-full pointer-events-none"
            viewBox="0 0 700 580"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* Top Node to Center Card */}
            <path
              d="M 280 85 C 280 160 320 220 380 260"
              stroke="#3DCCFF"
              strokeWidth="2"
              strokeDasharray="5 5"
              strokeOpacity="0.85"
            />
            {/* Left Node to Center Card */}
            <path
              d="M 120 250 C 220 250 280 290 350 310"
              stroke="#3DCCFF"
              strokeWidth="2"
              strokeDasharray="5 5"
              strokeOpacity="0.8"
            />
            {/* Bottom Node to Center Card */}
            <path
              d="M 250 490 C 280 430 330 390 360 370"
              stroke="#3DCCFF"
              strokeWidth="2"
              strokeDasharray="5 5"
              strokeOpacity="0.8"
            />
            {/* Center Card to Right Course Card */}
            <path
              d="M 480 300 C 530 280 560 250 590 230"
              stroke="#3DCCFF"
              strokeWidth="2"
              strokeDasharray="5 5"
              strokeOpacity="0.85"
            />
            {/* Center Card to Right Agent */}
            <path
              d="M 490 330 C 540 340 570 370 600 370"
              stroke="#3DCCFF"
              strokeWidth="2"
              strokeDasharray="5 5"
              strokeOpacity="0.75"
            />
            {/* Center Card to Collaboration Dialogue */}
            <path
              d="M 470 380 C 510 430 540 450 570 470"
              stroke="#3DCCFF"
              strokeWidth="2"
              strokeDasharray="5 5"
              strokeOpacity="0.75"
            />
          </svg>

          {/* Agent Node 1 (Top): UI/UX Master */}
          <div className="absolute left-[36%] top-3 -translate-x-1/2 flex flex-col items-center gap-1.5 z-20 group cursor-pointer animate-float">
            <div className="h-16 w-16 rounded-full bg-white/60 border-2 border-white/85 shadow-soft p-1 flex items-center justify-center backdrop-blur-2xl ring-1 ring-inset ring-white/70 transition-transform group-hover:scale-110">
              <div className="h-full w-full rounded-full bg-gradient-to-tr from-sky-200 to-indigo-100 flex items-center justify-center text-indigo-700">
                <Bot className="w-8 h-8 text-[#252229]" />
              </div>
            </div>
            <span className="px-3.5 py-1 rounded-full bg-white/65 border border-white/85 text-[11px] font-semibold text-ink shadow-sm backdrop-blur-xl ring-1 ring-inset ring-white/70">
              UI/UX Master
            </span>
          </div>

          {/* Agent Node 2 (Left): Coding Coach */}
          <div className="absolute left-6 top-[38%] flex flex-col items-center gap-1.5 z-20 group cursor-pointer animate-float-delayed">
            <div className="h-15 w-15 rounded-full bg-white/60 border-2 border-white/85 shadow-soft p-1 flex items-center justify-center backdrop-blur-2xl ring-1 ring-inset ring-white/70 transition-transform group-hover:scale-110">
              <div className="h-full w-full rounded-full bg-gradient-to-tr from-cyan-100 to-blue-200 flex items-center justify-center text-blue-700">
                <BrainCircuit className="w-7 h-7 text-[#252229]" />
              </div>
            </div>
            <span className="px-3.5 py-1 rounded-full bg-white/65 border border-white/85 text-[11px] font-semibold text-ink shadow-sm backdrop-blur-xl ring-1 ring-inset ring-white/70">
              Coding Coach
            </span>
          </div>

          {/* Agent Node 3 (Bottom): Data Guide */}
          <div className="absolute left-[32%] bottom-4 flex flex-col items-center gap-1.5 z-20 group cursor-pointer animate-float">
            <div className="h-15 w-15 rounded-full bg-white/60 border-2 border-white/85 shadow-soft p-1 flex items-center justify-center backdrop-blur-2xl ring-1 ring-inset ring-white/70 transition-transform group-hover:scale-110">
              <div className="h-full w-full rounded-full bg-gradient-to-tr from-amber-100 to-rose-200 flex items-center justify-center text-rose-700">
                <Bot className="w-7 h-7 text-[#252229]" />
              </div>
            </div>
            <span className="px-3.5 py-1 rounded-full bg-white/65 border border-white/85 text-[11px] font-semibold text-ink shadow-sm backdrop-blur-xl ring-1 ring-inset ring-white/70">
              Data Guide
            </span>
          </div>

          {/* Agent Node 4 (Right): Quiz Evaluator */}
          <div className="absolute right-6 top-[55%] flex flex-col items-center gap-1.5 z-20 group cursor-pointer animate-float-delayed">
            <div className="h-14 w-14 rounded-full bg-white/60 border-2 border-white/85 shadow-soft p-1 flex items-center justify-center backdrop-blur-2xl ring-1 ring-inset ring-white/70 transition-transform group-hover:scale-110">
              <div className="h-full w-full rounded-full bg-gradient-to-tr from-emerald-100 to-teal-200 flex items-center justify-center text-teal-800">
                <Bot className="w-6 h-6 text-[#252229]" />
              </div>
            </div>
            <span className="px-3.5 py-1 rounded-full bg-white/65 border border-white/85 text-[11px] font-semibold text-ink shadow-sm backdrop-blur-xl ring-1 ring-inset ring-white/70">
              Quiz Evaluator
            </span>
          </div>

          {/* Top Center-Right Floating Card: Active Agents Network */}
          <div className="absolute right-12 top-2 p-3 sm:p-3.5 rounded-2xl bg-[#E0F2FE]/55 border border-[#BAE6FD]/85 shadow-[0_16px_40px_-8px_rgba(14,165,233,0.16)] backdrop-blur-2xl ring-1 ring-inset ring-white/80 flex items-center gap-4 z-30">
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <p className="text-xs font-bold text-ink">Active Agents Network</p>
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  Live
                </span>
              </div>
              <div className="flex items-center gap-3 text-[10px] text-muted">
                <div className="flex items-center -space-x-1.5">
                  <div className="w-5 h-5 rounded-full bg-sky-400 border border-white flex items-center justify-center text-[9px] font-bold text-white shadow-xs">
                    A
                  </div>
                  <div className="w-5 h-5 rounded-full bg-rose-400 border border-white flex items-center justify-center text-[9px] font-bold text-white shadow-xs">
                    B
                  </div>
                  <div className="w-5 h-5 rounded-full bg-purple-400 border border-white flex items-center justify-center text-[9px] font-bold text-white shadow-xs">
                    C
                  </div>
                </div>
                <span>4 Tutors Active</span>
              </div>
            </div>
          </div>

          {/* Floating Pill: 12 Active Courses */}
          <div className="absolute right-3 top-20 p-2.5 px-3.5 rounded-2xl bg-white/60 border border-white/85 shadow-[0_12px_32px_rgba(40,30,60,0.10)] backdrop-blur-2xl ring-1 ring-inset ring-white/75 flex items-center gap-2.5 z-20">
            <div className="h-7 w-7 rounded-xl bg-gradient-to-tr from-cyan-400 to-blue-500 flex items-center justify-center text-white shadow-sm">
              <Layers className="w-4 h-4" />
            </div>
            <div className="text-left text-xs">
              <p className="font-bold text-ink">12</p>
              <p className="text-[10px] text-muted -mt-0.5">Active Courses</p>
            </div>
          </div>

          {/* MAIN CENTERPIECE: Featured UI/UX Masterclass Glass Card */}
          <div className="absolute left-[44%] top-[48%] -translate-x-1/2 -translate-y-1/2 w-64 sm:w-72 rounded-3xl bg-white/60 border border-white/90 shadow-[0_24px_60px_-10px_rgba(40,30,60,0.16)] backdrop-blur-3xl ring-1 ring-inset ring-white/80 p-3.5 z-30 transition-all hover:-translate-y-[52%] group/card">
            {/* Visual Image Showcase with Generated 3D Robot Tutor */}
            <div className="relative w-full h-36 rounded-2xl overflow-hidden bg-slate-900 flex flex-col justify-between p-3.5 text-white shadow-inner">
              <img
                src="/images/robot_tutor.jpg"
                alt="AI Robot Tutor UI/UX Masterclass"
                className="absolute inset-0 w-full h-full object-cover object-center group-hover/card:scale-105 transition-transform duration-500"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/25 to-black/35" />
              <div className="relative z-10 flex items-center justify-between">
                <span className="px-2 py-0.5 rounded-md bg-white/25 text-[10px] font-semibold backdrop-blur-md border border-white/30">
                  Active Sprint
                </span>
                <span className="h-2 w-2 rounded-full bg-cyan-400 animate-ping" />
              </div>
              <div className="relative z-10 space-y-0.5">
                <p className="text-[11px] text-cyan-200 font-medium">Week 1 • Lesson 3</p>
                <h4 className="text-sm font-bold tracking-tight text-white leading-tight drop-shadow-sm">
                  Visual Hierarchy & Typography
                </h4>
              </div>
            </div>

            {/* Title & Metadata */}
            <div className="mt-3 space-y-2 text-left">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-ink">UI/UX Design Masterclass</h3>
                <div className="flex items-center gap-1 text-xs font-bold text-amber-600">
                  <Star className="w-3.5 h-3.5 fill-amber-500 text-amber-500" />
                  <span>4.9</span>
                </div>
              </div>

              <div className="flex items-center gap-2 text-[11px] text-muted">
                <span>Beginner</span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  8h 30m
                </span>
              </div>

              {/* Progress bar */}
              <div className="pt-1">
                <div className="w-full h-1.5 bg-black/10 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-cyan-400 to-blue-500 w-[68%] rounded-full" />
                </div>
              </div>
            </div>
          </div>

          {/* Right Floating Card: UI/UX Status */}
          <div className="absolute right-0 top-[34%] w-60 rounded-2xl bg-[#FFEDD5]/55 border border-[#FED7AA]/85 shadow-[0_16px_40px_-8px_rgba(249,115,22,0.12)] backdrop-blur-2xl ring-1 ring-inset ring-white/80 p-3 z-20 hidden sm:block text-left">
            <h4 className="text-xs font-bold text-ink">UI/UX Design Masterclass</h4>
            <div className="flex items-center justify-between text-[10px] text-muted mt-1 mb-2">
              <span className="flex items-center gap-1">
                <Clock className="w-2.5 h-2.5" />
                Beginner • 8h 30m
              </span>
              <span className="font-bold text-amber-600 flex items-center gap-0.5">
                <Star className="w-2.5 h-2.5 fill-amber-500 text-amber-500" />
                4.9
              </span>
            </div>
            <div className="w-full h-1.5 bg-black/10 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 w-[72%] rounded-full" />
            </div>
          </div>

          {/* Right Bottom Floating Card: AI Collaboration Dialogue */}
          <div className="absolute right-2 bottom-8 w-64 rounded-2xl bg-[#EDE9FE]/60 border border-[#DDD6FE]/85 shadow-[0_16px_40px_-8px_rgba(139,92,246,0.12)] backdrop-blur-2xl ring-1 ring-inset ring-white/80 p-3.5 z-20 hidden sm:block text-left">
            <div className="flex items-center gap-1.5 text-xs font-bold text-ink mb-1.5">
              <MessageSquare className="w-3.5 h-3.5 text-violet" />
              <span>AI Collaboration</span>
            </div>
            <p className="text-[10px] text-muted leading-relaxed font-mono">
              <span className="text-blue-700 font-semibold">Tutor A:</span> "Let's introduce typography."
              <br />
              <span className="text-purple-700 font-semibold">→ Tutor B:</span> "I'll generate the quiz."
            </p>
          </div>

          {/* Bottom Floating Pill: Connected AI Assistants */}
          <div className="absolute right-28 bottom-2 p-2.5 px-4 rounded-2xl bg-white/60 border border-white/85 shadow-[0_12px_32px_rgba(40,30,60,0.10)] backdrop-blur-2xl ring-1 ring-inset ring-white/75 flex items-center gap-2.5 z-20">
            <div className="h-6 w-6 rounded-lg bg-cyan-100 flex items-center justify-center text-cyan-800">
              <Radio className="w-3.5 h-3.5" />
            </div>
            <span className="text-xs font-bold text-ink">Connected AI Assistants</span>
          </div>
        </div>

        {/* Multi-layered flowing 3D wave ribbons at the base of the Hero Section spanning canvas full-bleed */}
        <div className="col-span-1 lg:col-span-12 w-screen max-w-[1440px] relative left-1/2 -translate-x-1/2 h-36 sm:h-48 overflow-hidden pointer-events-none -mb-12 mt-4">
          <svg
            className="w-full h-full object-fill"
            viewBox="0 0 1440 220"
            fill="none"
            preserveAspectRatio="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <defs>
              <linearGradient id="hero-wave-lavender" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#93C5FD" stopOpacity="0.55" />
                <stop offset="50%" stopColor="#C4B5FD" stopOpacity="0.7" />
                <stop offset="100%" stopColor="#FDA4AF" stopOpacity="0.65" />
              </linearGradient>
              <linearGradient id="hero-wave-coral" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#FB923C" stopOpacity="0.75" />
                <stop offset="40%" stopColor="#F87171" stopOpacity="0.82" />
                <stop offset="70%" stopColor="#F472B6" stopOpacity="0.78" />
                <stop offset="100%" stopColor="#60A5FA" stopOpacity="0.65" />
              </linearGradient>
              <linearGradient id="hero-wave-foreground" x1="0%" y1="50%" x2="100%" y2="50%">
                <stop offset="0%" stopColor="#EA580C" stopOpacity="0.8" />
                <stop offset="30%" stopColor="#F43F5E" stopOpacity="0.88" />
                <stop offset="60%" stopColor="#FB7185" stopOpacity="0.85" />
                <stop offset="90%" stopColor="#38BDF8" stopOpacity="0.9" />
                <stop offset="100%" stopColor="#0284C7" stopOpacity="0.8" />
              </linearGradient>
              <linearGradient id="hero-wave-crest" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#0284C7" stopOpacity="0.95" />
                <stop offset="40%" stopColor="#F43F5E" stopOpacity="1" />
                <stop offset="75%" stopColor="#6366F1" stopOpacity="1" />
                <stop offset="100%" stopColor="#0EA5E9" stopOpacity="0.95" />
              </linearGradient>
            </defs>
            <path
              d="M0,130 C240,70 480,180 720,120 C960,60 1200,160 1440,100 L1440,220 L0,220 Z"
              fill="url(#hero-wave-lavender)"
            />
            <path
              d="M0,160 C280,110 520,210 800,140 C1080,70 1280,180 1440,130 L1440,220 L0,220 Z"
              fill="url(#hero-wave-coral)"
            />
            <path
              d="M0,180 C200,150 420,210 680,160 C940,110 1180,190 1440,150 L1440,220 L0,220 Z"
              fill="url(#hero-wave-foreground)"
            />
            <path
              d="M0,180 C200,150 420,210 680,160 C940,110 1180,190 1440,150"
              stroke="url(#hero-wave-crest)"
              strokeWidth="2.5"
              fill="none"
              strokeLinecap="round"
            />
          </svg>
        </div>
      </section>

      {/* Feature Pillars: How LearnWeave AI Functions */}
      <section aria-labelledby="features-title" className="space-y-10 pt-4">
        <div className="text-center space-y-2.5 max-w-2xl mx-auto">
          <Badge variant="accent">End-to-End Learning Engine</Badge>
          <h2 id="features-title" className="text-3xl sm:text-4xl font-display text-ink">
            Deep, Long-Term Mastery Grounded in Your Study Notes
          </h2>
          <p className="text-sm text-muted">
            LearnWeave brings RAG document retrieval, multi-agent lesson generation, and spaced repetition together.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <GlassCard variant="sky" padding="md" className="space-y-3.5 hover:shadow-soft transition-all">
            <div className="h-11 w-11 rounded-2xl bg-sky-200/50 border border-sky-300/60 flex items-center justify-center text-blue-900 font-bold">
              <Target className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold text-ink">1. Goal Intake & Roadmap</h3>
            <p className="text-xs text-muted leading-relaxed">
              Define your subject, timeframe, and study pace. The RoadmapPlanningAgent constructs a two-week sprint.
            </p>
          </GlassCard>

          <GlassCard variant="peach" padding="md" className="space-y-3.5 hover:shadow-soft transition-all">
            <div className="h-11 w-11 rounded-2xl bg-orange-200/50 border border-orange-300/60 flex items-center justify-center text-orange-950 font-bold">
              <FileText className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold text-ink">2. RAG Document Ingestion</h3>
            <p className="text-xs text-muted leading-relaxed">
              Upload PDF or text lecture notes. Semantic chunking and vector indexing ground answers in your real materials.
            </p>
          </GlassCard>

          <GlassCard variant="lavender" padding="md" className="space-y-3.5 hover:shadow-soft transition-all">
            <div className="h-11 w-11 rounded-2xl bg-purple-200/50 border border-purple-300/60 flex items-center justify-center text-indigo-950 font-bold">
              <BrainCircuit className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold text-ink">3. 6-Step Learning Cycle</h3>
            <p className="text-xs text-muted leading-relaxed">
              Engage with lesson explanations, Kokoro voice narration, Whisper speech doubt asking, and formative quizzes.
            </p>
          </GlassCard>

          <GlassCard variant="mint" padding="md" className="space-y-3.5 hover:shadow-soft transition-all">
            <div className="h-11 w-11 rounded-2xl bg-emerald-200/50 border border-emerald-300/60 flex items-center justify-center text-emerald-950 font-bold">
              <Compass className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold text-ink">4. Spaced Repetition</h3>
            <p className="text-xs text-muted leading-relaxed">
              Automated review sessions are scheduled at +3 and +7 days. Scores below 70% trigger adaptive remediation.
            </p>
          </GlassCard>
        </div>
      </section>

      {/* Community Banner */}
      <section className="relative overflow-hidden rounded-3xl p-6 sm:p-10 bg-white/50 border border-white/80 shadow-glass backdrop-blur-2xl ring-1 ring-inset ring-white/75 flex flex-col md:flex-row items-center justify-between gap-6 text-left">
        <div className="space-y-2 max-w-xl">
          <span className="text-[11px] font-bold uppercase tracking-wider text-cyan-800 bg-cyan-100 px-2.5 py-1 rounded-full border border-cyan-200">
            Open Knowledge Base
          </span>
          <h3 className="text-2xl sm:text-3xl font-display text-ink font-semibold">
            Discover & Import Community Study Notes
          </h3>
          <p className="text-xs sm:text-sm text-muted leading-relaxed">
            Browse peer-reviewed course notes ranked by Wilson confidence scoring. Import any public note directly into your private workspace with independent semantic chunk cloning.
          </p>
        </div>
        <div className="flex-shrink-0">
          <Link to="/community">
            <button
              type="button"
              className="px-6 py-3 rounded-full bg-[#252229] hover:bg-[#151318] text-white text-xs font-semibold shadow-md transition-all active:scale-95"
            >
              Browse Community Library
            </button>
          </Link>
        </div>
      </section>
    </div>
  );
}
