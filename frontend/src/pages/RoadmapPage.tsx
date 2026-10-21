import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api";
import type { RoadmapDetailResponse, LessonResponse } from "@/api/types";
import { GlassCard } from "@/components/ui/GlassCard";
import { Badge } from "@/components/ui/Badge";
import { GoalIntakeModal } from "@/features/goals/GoalIntakeModal";
import { LearningCycleModal } from "@/features/lesson/LearningCycleModal";
import { useToast } from "@/components/ui/Toast";
import {
  Compass,
  CheckCircle2,
  Circle,
  Clock,
  Lock,
  Sparkles,
  ChevronRight,
  BookOpen,
  Calendar,
  AlertCircle,
  Play,
  RotateCw,
  Plus,
  History,
  Layers,
} from "lucide-react";

export default function RoadmapPage(): JSX.Element {
  const [roadmap, setRoadmap] = useState<RoadmapDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [updatingLessonId, setUpdatingLessonId] = useState<string | null>(null);
  const [isGoalModalOpen, setIsGoalModalOpen] = useState(false);
  const [selectedLesson, setSelectedLesson] = useState<LessonResponse | null>(null);
  const [isCycleModalOpen, setIsCycleModalOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toast = useToast();

  const fetchRoadmap = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getActiveRoadmap();
      setRoadmap(data);
    } catch (err: any) {
      if (err?.status === 404) {
        setRoadmap(null);
      } else {
        setError(err?.message || "Failed to load active roadmap.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRoadmap();
  }, []);

  const handleToggleLessonStatus = async (lesson: LessonResponse, e: React.MouseEvent) => {
    e.stopPropagation();
    const nextStatus =
      lesson.status === "completed"
        ? "pending"
        : lesson.status === "in_progress"
        ? "completed"
        : "in_progress";

    setUpdatingLessonId(lesson.id);
    try {
      await api.updateLessonStatus(lesson.id, nextStatus);
      toast.success(`Lesson marked as ${nextStatus}`);
      await fetchRoadmap();
    } catch (err: any) {
      toast.error(err?.message || "Failed to update lesson status");
    } finally {
      setUpdatingLessonId(null);
    }
  };

  const handleOpenCycle = (lesson: LessonResponse) => {
    setSelectedLesson(lesson);
    setIsCycleModalOpen(true);
  };

  if (isLoading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center space-y-3">
        <RotateCw className="w-8 h-8 text-muted animate-spin" />
        <p className="text-xs font-semibold text-muted">Loading your personalized roadmap...</p>
      </div>
    );
  }

  if (!roadmap) {
    return (
      <div className="py-16 px-4 max-w-xl mx-auto text-center space-y-6">
        <div className="p-10 sm:p-14 rounded-3xl bg-white/55 border border-white/85 shadow-[0_16px_40px_-10px_rgba(40,30,60,0.08)] ring-1 ring-inset ring-white/80 backdrop-blur-2xl text-center space-y-6">
          <div className="w-16 h-16 rounded-3xl bg-cyan-100/90 border border-cyan-200 text-cyan-800 flex items-center justify-center mx-auto shadow-inner">
            <Compass className="w-8 h-8" />
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-ink">No Active Learning Roadmap</h2>
            <p className="text-xs sm:text-sm text-muted leading-relaxed">
              Synthesize a structured learning journey tailored to your background and weekly study hours.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setIsGoalModalOpen(true)}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-[#252229] hover:bg-[#151318] text-white text-xs font-semibold shadow-md active:scale-95 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Create Learning Goal</span>
          </button>
        </div>

        <GoalIntakeModal
          isOpen={isGoalModalOpen}
          onClose={() => setIsGoalModalOpen(false)}
          onSuccess={() => fetchRoadmap()}
        />
      </div>
    );
  }

  // Modules division: active sprint (target_week <= 2) vs future planned (target_week > 2)
  const activeModules = roadmap.modules.filter((m) => m.target_week <= 2);
  const futureModules = roadmap.modules.filter((m) => m.target_week > 2);

  let totalActiveLessons = 0;
  let completedCount = 0;
  activeModules.forEach((m) => {
    m.lessons.forEach((l) => {
      totalActiveLessons++;
      if (l.status === "completed") completedCount++;
    });
  });

  const progressPercent =
    totalActiveLessons > 0 ? Math.round((completedCount / totalActiveLessons) * 100) : 0;

  return (
    <div className="py-6 sm:py-10 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-8 text-left animate-in fade-in duration-200">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-3xl p-6 sm:p-8 bg-white/55 border border-white/85 shadow-[0_16px_40px_-10px_rgba(40,30,60,0.08)] ring-1 ring-inset ring-white/80 backdrop-blur-2xl flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2 max-w-xl">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-cyan-100/90 text-cyan-800 border border-cyan-200/80 shadow-xs">
              Active Roadmap v{roadmap.version}
            </span>
            <span className="text-xs text-muted font-medium">
              {roadmap.total_modules} Modules • {roadmap.total_lessons} Lessons
            </span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-display text-ink font-semibold tracking-tight">
            {roadmap.title}
          </h1>

          <div className="flex items-center gap-4 text-xs font-semibold text-cyan-800 pt-1">
            <Link
              to={`/roadmaps/${roadmap.id}/history`}
              className="inline-flex items-center gap-1.5 hover:underline"
            >
              <History className="w-3.5 h-3.5" />
              <span>Version History</span>
            </Link>
            <span>•</span>
            <Link to="/schedule" className="inline-flex items-center gap-1.5 hover:underline">
              <Calendar className="w-3.5 h-3.5" />
              <span>Study Schedule</span>
            </Link>
          </div>
        </div>

        {/* Sprint Progress Pill Card */}
        <div className="w-full md:w-68 p-5 rounded-2xl bg-white/70 border border-white/85 ring-1 ring-inset ring-white/80 shadow-soft backdrop-blur-xl space-y-2">
          <div className="flex justify-between items-center text-xs font-bold text-ink">
            <span>Sprint Progress</span>
            <span className="font-mono text-cyan-700">{progressPercent}%</span>
          </div>
          <div className="w-full h-2 bg-black/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-cyan-400 to-blue-500 rounded-full transition-all duration-500"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <p className="text-[11px] text-muted text-right font-medium">
            {completedCount} of {totalActiveLessons} lessons completed
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-danger/10 border border-danger/20 text-xs text-danger font-medium flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          <span>{error}</span>
        </div>
      )}

      {/* SECTION 1: Active 2-Week Learning Sprint */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <h2 className="text-lg font-bold text-ink">Active 2-Week Learning Sprint</h2>
          </div>
          <span className="text-xs text-muted">
            Detailed lessons synthesized by RoadmapPlanningAgent
          </span>
        </div>

        <div className="space-y-5">
          {activeModules.map((module) => (
            <div
              key={module.id}
              className="rounded-3xl p-6 bg-white/55 border border-white/85 shadow-[0_16px_40px_-10px_rgba(40,30,60,0.08)] ring-1 ring-inset ring-white/80 backdrop-blur-2xl space-y-4"
            >
              {/* Module Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-surface-border/60 pb-3">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-black/5 text-muted">
                      Week {module.target_week}
                    </span>
                    <h3 className="text-base font-bold text-ink">{module.title}</h3>
                  </div>
                  {module.description && (
                    <p className="text-xs text-muted">{module.description}</p>
                  )}
                </div>
                <span className="text-xs text-muted flex items-center gap-1 font-mono">
                  <Clock className="w-3.5 h-3.5" />
                  ~{module.estimated_hours}h estimated
                </span>
              </div>

              {/* Lessons List */}
              <div className="grid grid-cols-1 gap-3">
                {module.lessons.map((lesson) => {
                  const isCompleted = lesson.status === "completed";
                  const isInProgress = lesson.status === "in_progress";

                  return (
                    <div
                      key={lesson.id}
                      onClick={() => handleOpenCycle(lesson)}
                      className={`p-4 rounded-2xl border transition-all cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-4 group ${
                        isCompleted
                          ? "bg-white/40 border-white/60 ring-1 ring-inset ring-white/40 opacity-80 backdrop-blur-sm"
                          : isInProgress
                          ? "bg-[#E0F2FE]/55 border-[#BAE6FD]/90 ring-1 ring-inset ring-white/90 shadow-md backdrop-blur-xl"
                          : "bg-white/60 hover:bg-white/85 border-white/80 ring-1 ring-inset ring-white/70 hover:shadow-soft backdrop-blur-md"
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        {/* Status Toggle Button */}
                        <button
                          type="button"
                          onClick={(e) => handleToggleLessonStatus(lesson, e)}
                          disabled={updatingLessonId === lesson.id}
                          className="mt-0.5 text-muted hover:text-ink transition-transform active:scale-90"
                          title="Click to toggle lesson status"
                        >
                          {isCompleted ? (
                            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                          ) : isInProgress ? (
                            <div className="w-5 h-5 rounded-full border-2 border-cyan-500 border-t-transparent animate-spin" />
                          ) : (
                            <Circle className="w-5 h-5 text-muted" />
                          )}
                        </button>

                        <div className="space-y-1">
                          <h4
                            className={`text-xs sm:text-sm font-bold ${
                              isCompleted ? "line-through text-muted" : "text-ink"
                            }`}
                          >
                            {lesson.title}
                          </h4>

                          {lesson.learning_objectives && lesson.learning_objectives.length > 0 && (
                            <p className="text-[11px] text-muted">
                              {lesson.learning_objectives.slice(0, 2).join(" • ")}
                            </p>
                          )}
                        </div>
                      </div>

                      {/* Right Meta & Action */}
                      <div className="flex items-center gap-3 self-end sm:self-center">
                        <span className="text-[11px] text-muted flex items-center gap-1 font-mono">
                          <Clock className="w-3 h-3" />
                          {lesson.duration_minutes}m
                        </span>

                        <span
                          className={`text-[10px] font-bold px-2.5 py-1 rounded-full ${
                            isCompleted
                              ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
                              : isInProgress
                              ? "bg-cyan-100 text-cyan-800 border border-cyan-200"
                              : "bg-black/5 text-muted"
                          }`}
                        >
                          {lesson.status}
                        </span>

                        <button
                          type="button"
                          className="p-2 rounded-xl bg-black/5 group-hover:bg-[#252229] group-hover:text-white transition-colors"
                          title="Start or Resume Learning Cycle"
                        >
                          <Play className="w-3.5 h-3.5 fill-current" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* SECTION 2: Future Planned Modules (Weeks 3+) */}
      {futureModules.length > 0 && (
        <div className="space-y-4 pt-4 border-t border-surface-border/60">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Lock className="w-4 h-4 text-muted" />
              <h2 className="text-base font-bold text-muted">Future Modules (Weeks 3+)</h2>
            </div>
            <span className="text-xs text-muted">
              Dynamically refined based on your mastery evaluations
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {futureModules.map((m) => (
              <div
                key={m.id}
                className="p-5 rounded-2xl bg-white/40 border border-white/60 ring-1 ring-inset ring-white/50 backdrop-blur-md space-y-2 opacity-80"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-black/5 text-muted">
                    Week {m.target_week}
                  </span>
                  <span className="text-[11px] text-muted">~{m.estimated_hours}h</span>
                </div>
                <h4 className="text-sm font-semibold text-ink">{m.title}</h4>
                <p className="text-xs text-muted">{m.description || "Future curriculum unit."}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Goal Intake Modal */}
      <GoalIntakeModal
        isOpen={isGoalModalOpen}
        onClose={() => setIsGoalModalOpen(false)}
        onSuccess={() => fetchRoadmap()}
      />

      {/* 6-Step Learning Cycle Modal */}
      <LearningCycleModal
        lesson={selectedLesson}
        isOpen={isCycleModalOpen}
        onClose={() => {
          setIsCycleModalOpen(false);
          setSelectedLesson(null);
          fetchRoadmap();
        }}
        onLessonCompleted={() => fetchRoadmap()}
      />
    </div>
  );
}
