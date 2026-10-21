import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api";
import type { ScheduleItem, RoadmapDetailResponse } from "@/api/types";
import { GlassCard } from "@/components/ui/GlassCard";
import { useToast } from "@/components/ui/Toast";
import {
  Calendar as CalendarIcon,
  Clock,
  CheckCircle2,
  Circle,
  RefreshCw,
  Sparkles,
  RotateCw,
  AlertCircle,
  Layers,
  ArrowRight,
} from "lucide-react";

export default function SchedulePage(): JSX.Element {
  const [schedule, setSchedule] = useState<ScheduleItem[]>([]);
  const [roadmap, setRoadmap] = useState<RoadmapDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [completingId, setCompletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const toast = useToast();

  const fetchScheduleAndRoadmap = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const activeRoadmap = await api.getActiveRoadmap().catch(() => null);
      setRoadmap(activeRoadmap);

      if (activeRoadmap?.id) {
        const sessions = await api.getSchedule(activeRoadmap.id);
        setSchedule(sessions || []);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load study schedule.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchScheduleAndRoadmap();
  }, []);

  const handleGenerateSchedule = async () => {
    if (!roadmap?.id) return;
    setIsGenerating(true);
    setError(null);
    try {
      const updated = await api.generateSchedule(roadmap.id);
      setSchedule(updated || []);
      toast.success("Schedule regenerated respecting daily capacity and spaced repetition!");
    } catch (err: any) {
      toast.error(err?.message || "Failed to generate schedule.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCompleteSession = async (item: ScheduleItem) => {
    if (item.status === "completed") return;
    setCompletingId(item.id);
    try {
      await api.completeScheduleSession(item.id);
      setSchedule((prev) =>
        prev.map((s) => (s.id === item.id ? { ...s, status: "completed" } : s))
      );
      toast.success("Study session marked as completed!");
    } catch (err: any) {
      toast.error(err?.message || "Failed to update session status.");
    } finally {
      setCompletingId(null);
    }
  };

  const completedSessions = schedule.filter((s) => s.status === "completed").length;
  const spacedSessions = schedule.filter((s) => s.session_type === "spaced_repetition").length;

  return (
    <div className="py-6 sm:py-10 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-8 text-left animate-in fade-in duration-200">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-3xl p-6 sm:p-8 bg-white/55 border border-white/85 shadow-[0_16px_40px_-10px_rgba(40,30,60,0.08)] ring-1 ring-inset ring-white/80 backdrop-blur-2xl flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2 max-w-xl">
          <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-emerald-100/90 text-emerald-800 border border-emerald-200/80 shadow-xs">
            Spaced Repetition Scheduler
          </span>
          <h1 className="text-2xl sm:text-3xl font-display text-ink font-semibold tracking-tight">
            Adaptive Study Planner
          </h1>
          <p className="text-xs sm:text-sm text-muted">
            Distributes your roadmap lessons across calendar dates respecting your daily learning capacity.
            Automated spaced repetition reviews are placed at +3 days and +7 days to cement memory retention.
          </p>
        </div>

        {roadmap && (
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleGenerateSchedule}
              disabled={isGenerating}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#252229] hover:bg-[#151318] disabled:opacity-50 text-white text-xs font-semibold shadow-md active:scale-95 transition-all"
            >
              {isGenerating ? (
                <>
                  <RotateCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Generating Schedule...</span>
                </>
              ) : (
                <>
                  <RefreshCw className="w-3.5 h-3.5 text-cyan-300" />
                  <span>Regenerate Schedule</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-danger/10 border border-danger/20 text-xs text-danger font-medium flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          <span>{error}</span>
        </div>
      )}

      {/* Metrics Row - Multi-tinted frosted GlassCard variants */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <GlassCard variant="sky" padding="md" className="space-y-1 text-left">
          <p className="text-xs font-semibold text-cyan-900">Total Sessions</p>
          <p className="text-2xl font-bold font-mono text-ink">{schedule.length}</p>
        </GlassCard>

        <GlassCard variant="mint" padding="md" className="space-y-1 text-left">
          <p className="text-xs font-semibold text-emerald-900">Completed Sessions</p>
          <p className="text-2xl font-bold font-mono text-emerald-600">{completedSessions}</p>
        </GlassCard>

        <GlassCard variant="lavender" padding="md" className="space-y-1 text-left">
          <p className="text-xs font-semibold text-purple-900">Spaced Repetition Reviews</p>
          <p className="text-2xl font-bold font-mono text-purple-600">{spacedSessions}</p>
        </GlassCard>
      </div>

      {isLoading ? (
        <div className="py-20 text-center text-xs text-muted">
          <RotateCw className="w-6 h-6 animate-spin mx-auto mb-2 text-muted" />
          Loading study schedule...
        </div>
      ) : !roadmap ? (
        <div className="p-12 rounded-3xl bg-white/55 border border-white/85 shadow-[0_16px_40px_-10px_rgba(40,30,60,0.08)] ring-1 ring-inset ring-white/80 backdrop-blur-2xl text-center space-y-4">
          <p className="text-base font-bold text-ink">No Active Roadmap Found</p>
          <p className="text-xs text-muted">
            Create a learning goal first to automatically generate your spaced study calendar.
          </p>
          <Link
            to="/onboarding"
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-full bg-[#252229] hover:bg-[#151318] text-white text-xs font-semibold shadow-md active:scale-95 transition-all"
          >
            <span>Create Goal</span>
          </Link>
        </div>
      ) : schedule.length === 0 ? (
        <div className="p-12 rounded-3xl bg-white/55 border border-white/85 shadow-[0_16px_40px_-10px_rgba(40,30,60,0.08)] ring-1 ring-inset ring-white/80 backdrop-blur-2xl text-center space-y-4">
          <CalendarIcon className="w-10 h-10 text-muted mx-auto" />
          <p className="text-sm font-bold text-ink">No Study Sessions Generated Yet</p>
          <p className="text-xs text-muted">
            Generate an automated spaced study schedule for your active roadmap.
          </p>
          <button
            type="button"
            onClick={handleGenerateSchedule}
            disabled={isGenerating}
            className="px-6 py-2.5 rounded-full bg-[#252229] hover:bg-[#151318] text-white text-xs font-semibold shadow-md active:scale-95 transition-all"
          >
            Generate Study Schedule
          </button>
        </div>
      ) : (
        /* Sessions Calendar Timeline */
        <div className="space-y-3">
          <h2 className="text-base font-bold text-ink">Planned Study Sessions ({schedule.length})</h2>

          <div className="grid grid-cols-1 gap-3">
            {schedule.map((item) => {
              const isCompleted = item.status === "completed";
              const isSpaced = item.session_type === "spaced_repetition";

              return (
                <div
                  key={item.id}
                  className={`p-4 rounded-2xl border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
                    isCompleted
                      ? "bg-white/40 border-white/60 ring-1 ring-inset ring-white/40 opacity-80 backdrop-blur-sm"
                      : isSpaced
                      ? "bg-[#EDE9FE]/50 border-[#DDD6FE]/90 ring-1 ring-inset ring-white/80 shadow-xs backdrop-blur-md"
                      : "bg-white/60 hover:bg-white/85 border-white/80 ring-1 ring-inset ring-white/70 shadow-xs backdrop-blur-md"
                  }`}
                >
                  <div className="flex items-center gap-3.5">
                    {/* Completion button */}
                    <button
                      type="button"
                      onClick={() => handleCompleteSession(item)}
                      disabled={isCompleted || completingId === item.id}
                      className="text-muted hover:text-ink transition-transform active:scale-90"
                      title={isCompleted ? "Session Completed" : "Mark as completed"}
                    >
                      {completingId === item.id ? (
                        <RotateCw className="w-5 h-5 animate-spin text-cyan-600" />
                      ) : isCompleted ? (
                        <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                      ) : (
                        <Circle className="w-5 h-5 text-muted hover:text-ink" />
                      )}
                    </button>

                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                            isSpaced
                              ? "bg-purple-100 text-purple-800 border border-purple-200"
                              : "bg-blue-100 text-blue-800 border border-blue-200"
                          }`}
                        >
                          {isSpaced ? "Spaced Repetition Review" : "Standard Lesson"}
                        </span>
                        <span className="text-[11px] font-mono text-muted flex items-center gap-1 font-medium">
                          <CalendarIcon className="w-3 h-3" />
                          {item.scheduled_date}
                        </span>
                      </div>

                      <h4
                        className={`text-xs sm:text-sm font-bold ${
                          isCompleted ? "line-through text-muted" : "text-ink"
                        }`}
                      >
                        {item.lesson_title || `Lesson ID: ${item.lesson_id.slice(0, 8)}`}
                      </h4>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 self-end sm:self-center">
                    <span className="text-xs text-muted flex items-center gap-1 font-mono">
                      <Clock className="w-3 h-3" />
                      {item.estimated_minutes} min
                    </span>

                    <span
                      className={`text-[10px] font-bold px-2.5 py-1 rounded-full ${
                        isCompleted
                          ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
                          : "bg-black/5 text-muted"
                      }`}
                    >
                      {item.status}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
