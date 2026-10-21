import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/features/auth/AuthProvider";
import { api } from "@/api";
import type { RoadmapDetailResponse, ScheduleItem, LessonResponse } from "@/api/types";
import { GlassCard } from "@/components/ui/GlassCard";
import { Badge } from "@/components/ui/Badge";
import { GoalIntakeModal } from "@/features/goals/GoalIntakeModal";
import { LearningCycleModal } from "@/features/lesson/LearningCycleModal";
import {
  Sparkles,
  Compass,
  BookOpen,
  Calendar,
  Users,
  Plus,
  Play,
  CheckCircle2,
  Clock,
  ArrowRight,
  Target,
  FileText,
  RotateCw,
  Award,
  Layers,
} from "lucide-react";

export default function DashboardPage(): JSX.Element {
  const { user } = useAuth();
  const [roadmap, setRoadmap] = useState<RoadmapDetailResponse | null>(null);
  const [schedule, setSchedule] = useState<ScheduleItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isGoalModalOpen, setIsGoalModalOpen] = useState(false);
  const [selectedLesson, setSelectedLesson] = useState<LessonResponse | null>(null);
  const [isCycleModalOpen, setIsCycleModalOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDashboardData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const activeRoadmap = await api.getActiveRoadmap().catch(() => null);
      setRoadmap(activeRoadmap);

      if (activeRoadmap?.id) {
        const scheduleData = await api.getSchedule(activeRoadmap.id).catch(() => []);
        setSchedule(scheduleData || []);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load dashboard data.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  // Compute active sprint metrics
  const activeModules = (roadmap?.modules || []).filter((m) => m.target_week <= 2);
  let totalActiveLessons = 0;
  let completedActiveLessons = 0;

  activeModules.forEach((m) => {
    m.lessons.forEach((l) => {
      totalActiveLessons++;
      if (l.status === "completed") {
        completedActiveLessons++;
      }
    });
  });

  const nextLessonToResume: LessonResponse | null = (() => {
    for (const m of activeModules) {
      for (const l of m.lessons) {
        if (l.status === "in_progress" || l.status === "pending") {
          return l;
        }
      }
    }
    return null;
  })();

  const progressPercent =
    totalActiveLessons > 0
      ? Math.round((completedActiveLessons / totalActiveLessons) * 100)
      : 0;

  const handleOpenLesson = (lesson: LessonResponse) => {
    setSelectedLesson(lesson);
    setIsCycleModalOpen(true);
  };

  const upcomingSessions = schedule
    .filter((s) => s.status === "pending")
    .slice(0, 3);

  return (
    <div className="py-6 sm:py-10 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-200">
      {/* Top Welcome Banner */}
      <div className="relative overflow-hidden rounded-3xl p-6 sm:p-8 bg-white/55 border border-white/85 shadow-[0_16px_40px_-10px_rgba(40,30,60,0.08)] ring-1 ring-inset ring-white/80 backdrop-blur-2xl flex flex-col md:flex-row md:items-center justify-between gap-6 text-left">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2">
            <span className="text-[11px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-cyan-100/90 text-cyan-800 border border-cyan-200/80 shadow-xs">
              Student Workspace
            </span>
            <span className="text-xs text-muted">
              {new Date().toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" })}
            </span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-display text-ink font-semibold tracking-tight">
            Welcome back, {user?.full_name || user?.email?.split("@")[0] || "Learner"}
          </h1>

          <p className="text-xs sm:text-sm text-muted max-w-xl">
            {roadmap
              ? `You are currently progressing through the 2-week active sprint for "${roadmap.title}".`
              : "Set your learning goal to synthesize your personalized adaptive learning roadmap."}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setIsGoalModalOpen(true)}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#252229] hover:bg-[#1a171d] text-white text-xs font-semibold shadow-md transition-all active:scale-95"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Learning Goal</span>
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="py-24 flex flex-col items-center justify-center space-y-3">
          <RotateCw className="w-8 h-8 text-muted animate-spin" />
          <p className="text-xs font-semibold text-muted">Loading your personalized workspace...</p>
        </div>
      ) : !roadmap ? (
        /* Empty State: No active roadmap */
        <div className="p-10 sm:p-14 rounded-3xl bg-white/55 border border-white/85 shadow-[0_16px_40px_-10px_rgba(40,30,60,0.08)] ring-1 ring-inset ring-white/80 text-center space-y-5 max-w-2xl mx-auto backdrop-blur-2xl">
          <div className="w-14 h-14 rounded-2xl bg-cyan-100/90 text-cyan-800 flex items-center justify-center mx-auto shadow-inner border border-cyan-200">
            <Target className="w-7 h-7" />
          </div>
          <div className="space-y-2">
            <h2 className="text-xl font-bold text-ink">No Active Learning Goal Found</h2>
            <p className="text-xs sm:text-sm text-muted leading-relaxed">
              Create your first learning goal. LearnWeave's agentic planner will synthesize a
              structured, adaptive 2-week sprint grounded in your pace and materials.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setIsGoalModalOpen(true)}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-[#252229] hover:bg-[#151318] text-white text-xs font-semibold shadow-md active:scale-95 transition-all"
          >
            <Sparkles className="w-4 h-4 text-cyan-300" />
            <span>Create Goal & Synthesize Roadmap</span>
          </button>
        </div>
      ) : (
        /* Active Dashboard Content */
        <div className="space-y-8">
          {/* Metrics Row - Multi-tinted frosted GlassCard variants */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <GlassCard variant="sky" padding="md" className="space-y-2 text-left">
              <div className="flex items-center justify-between text-muted text-xs">
                <span className="font-semibold text-cyan-900">Sprint Progress</span>
                <Compass className="w-4 h-4 text-cyan-600" />
              </div>
              <p className="text-2xl font-bold font-mono text-ink">{progressPercent}%</p>
              <div className="w-full h-1.5 bg-black/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-cyan-500 to-blue-600 rounded-full"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
              <p className="text-[10px] text-muted font-medium">
                {completedActiveLessons} of {totalActiveLessons} sprint lessons done
              </p>
            </GlassCard>

            <GlassCard variant="lavender" padding="md" className="space-y-2 text-left">
              <div className="flex items-center justify-between text-muted text-xs">
                <span className="font-semibold text-purple-900">Active Modules</span>
                <Layers className="w-4 h-4 text-violet-600" />
              </div>
              <p className="text-2xl font-bold font-mono text-ink">{activeModules.length}</p>
              <p className="text-[10px] text-muted font-medium">
                {roadmap.total_modules} total modules planned
              </p>
            </GlassCard>

            <GlassCard variant="mint" padding="md" className="space-y-2 text-left">
              <div className="flex items-center justify-between text-muted text-xs">
                <span className="font-semibold text-emerald-900">Pending Study Sessions</span>
                <Calendar className="w-4 h-4 text-emerald-600" />
              </div>
              <p className="text-2xl font-bold font-mono text-ink">
                {schedule.filter((s) => s.status === "pending").length}
              </p>
              <p className="text-[10px] text-muted font-medium">
                Spaced repetition reviews scheduled
              </p>
            </GlassCard>

            <GlassCard variant="peach" padding="md" className="space-y-2 text-left">
              <div className="flex items-center justify-between text-muted text-xs">
                <span className="font-semibold text-amber-900">Roadmap Version</span>
                <Award className="w-4 h-4 text-amber-600" />
              </div>
              <p className="text-2xl font-bold font-mono text-ink">v{roadmap.version}</p>
              <Link
                to={`/roadmaps/${roadmap.id}/history`}
                className="text-[10px] text-cyan-800 hover:underline font-semibold block"
              >
                View Version History →
              </Link>
            </GlassCard>
          </div>

          {/* Active Sprint Next Lesson & Schedule Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Next Lesson Callout */}
            <div className="lg:col-span-2 rounded-3xl p-6 bg-white/55 border border-white/85 shadow-[0_16px_40px_-10px_rgba(40,30,60,0.08)] ring-1 ring-inset ring-white/80 backdrop-blur-2xl text-left space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-muted">
                  Active 2-Week Learning Sprint
                </span>
                <Link
                  to="/roadmap"
                  className="text-xs font-semibold text-cyan-800 hover:text-ink flex items-center gap-1"
                >
                  <span>Open Full Roadmap</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>

              {nextLessonToResume ? (
                <div className="p-5 rounded-2xl bg-gradient-to-br from-white/75 via-amber-50/40 to-orange-50/40 border border-amber-200/80 ring-1 ring-inset ring-white/80 shadow-soft backdrop-blur-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded-md bg-amber-100 text-amber-800 text-[10px] font-bold uppercase border border-amber-200">
                        Up Next
                      </span>
                      <span className="text-xs text-muted font-medium flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {nextLessonToResume.duration_minutes} min
                      </span>
                    </div>
                    <h3 className="text-base font-bold text-ink">{nextLessonToResume.title}</h3>
                    {nextLessonToResume.learning_objectives?.length > 0 && (
                      <p className="text-xs text-muted">
                        Objectives: {nextLessonToResume.learning_objectives.slice(0, 2).join(", ")}
                      </p>
                    )}
                  </div>

                  <button
                    type="button"
                    onClick={() => handleOpenLesson(nextLessonToResume!)}
                    className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-full bg-[#252229] hover:bg-[#151318] text-white text-xs font-semibold shadow-md transition-all active:scale-95 flex-shrink-0"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>Resume Learning Cycle</span>
                  </button>
                </div>
              ) : (
                <div className="p-5 rounded-2xl bg-emerald-50/70 border border-emerald-200 ring-1 ring-inset ring-white/70 text-xs text-emerald-900 flex items-center gap-2 backdrop-blur-md">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
                  <span>All active sprint lessons completed! Ready to synthesize the next module.</span>
                </div>
              )}

              {/* Quick links row */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
                <Link
                  to="/notes"
                  className="p-3.5 rounded-2xl bg-white/45 hover:bg-white/75 border border-white/80 ring-1 ring-inset ring-white/70 backdrop-blur-md shadow-xs text-left transition-all hover:scale-[1.02] flex items-center gap-3"
                >
                  <div className="w-8 h-8 rounded-xl bg-rose-100 border border-rose-200 flex items-center justify-center text-rose-800">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-ink">Upload Notes</p>
                    <p className="text-[10px] text-muted">Ground lessons in PDF/TXT</p>
                  </div>
                </Link>

                <Link
                  to="/schedule"
                  className="p-3.5 rounded-2xl bg-white/45 hover:bg-white/75 border border-white/80 ring-1 ring-inset ring-white/70 backdrop-blur-md shadow-xs text-left transition-all hover:scale-[1.02] flex items-center gap-3"
                >
                  <div className="w-8 h-8 rounded-xl bg-emerald-100 border border-emerald-200 flex items-center justify-center text-emerald-900">
                    <Calendar className="w-4 h-4" />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-ink">Study Calendar</p>
                    <p className="text-[10px] text-muted">Paced daily schedule</p>
                  </div>
                </Link>

                <Link
                  to="/community"
                  className="p-3.5 rounded-2xl bg-white/45 hover:bg-white/75 border border-white/80 ring-1 ring-inset ring-white/70 backdrop-blur-md shadow-xs text-left transition-all hover:scale-[1.02] flex items-center gap-3"
                >
                  <div className="w-8 h-8 rounded-xl bg-cyan-100 border border-cyan-200 flex items-center justify-center text-cyan-900">
                    <Users className="w-4 h-4" />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-ink">Community Notes</p>
                    <p className="text-[10px] text-muted">Import shared knowledge</p>
                  </div>
                </Link>
              </div>
            </div>

            {/* Upcoming Spaced Repetition Sessions */}
            <div className="rounded-3xl p-6 bg-white/55 border border-white/85 shadow-[0_16px_40px_-10px_rgba(40,30,60,0.08)] ring-1 ring-inset ring-white/80 backdrop-blur-2xl text-left space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-muted">
                  Upcoming Sessions
                </span>
                <Link
                  to="/schedule"
                  className="text-xs font-semibold text-cyan-800 hover:text-ink"
                >
                  View All
                </Link>
              </div>

              {upcomingSessions.length === 0 ? (
                <div className="py-8 text-center text-xs text-muted">
                  No pending study sessions today.
                </div>
              ) : (
                <div className="space-y-2.5">
                  {upcomingSessions.map((item) => (
                    <div
                      key={item.id}
                      className="p-3 rounded-2xl bg-white/60 hover:bg-white/85 border border-white/80 ring-1 ring-inset ring-white/60 shadow-xs backdrop-blur-md flex items-center justify-between text-xs transition-all"
                    >
                      <div className="space-y-0.5">
                        <p className="font-semibold text-ink truncate max-w-[180px]">
                          {item.lesson_title || "Lesson Study"}
                        </p>
                        <p className="text-[10px] text-muted flex items-center gap-1.5">
                          <span>{item.scheduled_date}</span>
                          <span>•</span>
                          <span>{item.estimated_minutes} min</span>
                        </p>
                      </div>
                      <span
                        className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${
                          item.session_type === "spaced_repetition"
                            ? "bg-purple-100 text-purple-800 border border-purple-200"
                            : "bg-blue-100 text-blue-800 border border-blue-200"
                        }`}
                      >
                        {item.session_type === "spaced_repetition" ? "Review" : "Standard"}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Goal Intake Modal */}
      <GoalIntakeModal
        isOpen={isGoalModalOpen}
        onClose={() => setIsGoalModalOpen(false)}
        onSuccess={() => loadDashboardData()}
      />

      {/* 6-Step Learning Cycle Modal */}
      <LearningCycleModal
        lesson={selectedLesson}
        isOpen={isCycleModalOpen}
        onClose={() => {
          setIsCycleModalOpen(false);
          setSelectedLesson(null);
          loadDashboardData();
        }}
        onLessonCompleted={() => loadDashboardData()}
      />
    </div>
  );
}
