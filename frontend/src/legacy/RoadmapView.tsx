import React, { useState } from "react";
import {
  CheckCircle2,
  Circle,
  Clock,
  Lock,
  Sparkles,
  ChevronRight,
  BookOpen,
  Calendar,
  AlertCircle
} from "lucide-react";
import { Roadmap, Lesson, api } from "../api/client";

interface RoadmapViewProps {
  roadmap: Roadmap;
  onRefresh: () => void;
  onSelectLesson?: (lesson: Lesson) => void;
}

export const RoadmapView: React.FC<RoadmapViewProps> = ({ roadmap, onRefresh, onSelectLesson }) => {
  const [updatingLessonId, setUpdatingLessonId] = useState<string | null>(null);

  const activeModules = roadmap.modules.filter((m) => m.target_week <= 2);
  const futureModules = roadmap.modules.filter((m) => m.target_week > 2);

  // Compute progress
  let totalActiveLessons = 0;
  let completedCount = 0;
  activeModules.forEach((m) => {
    m.lessons.forEach((l) => {
      totalActiveLessons++;
      if (l.status === "completed") completedCount++;
    });
  });

  const progressPercent = totalActiveLessons > 0 ? Math.round((completedCount / totalActiveLessons) * 100) : 0;

  const handleToggleLessonStatus = async (lesson: Lesson) => {
    const nextStatus =
      lesson.status === "completed"
        ? "pending"
        : lesson.status === "in_progress"
        ? "completed"
        : "in_progress";

    setUpdatingLessonId(lesson.id);
    try {
      await api.updateLessonStatus(lesson.id, nextStatus);
      onRefresh();
    } catch (err) {
      console.error("Failed to update status:", err);
    } finally {
      setUpdatingLessonId(null);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-3xl p-6 sm:p-8 bg-gradient-to-br from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800 shadow-xl">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs uppercase font-bold tracking-wider px-2.5 py-1 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                Active Roadmap v{roadmap.version}
              </span>
              <span className="text-xs text-slate-400">
                {roadmap.total_modules} Modules • {roadmap.total_lessons} Lessons Total
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">{roadmap.title}</h1>
          </div>

          {/* Progress Card */}
          <div className="w-full md:w-64 glass-panel p-4 rounded-2xl border border-slate-800">
            <div className="flex justify-between items-center text-xs font-semibold mb-2 text-slate-300">
              <span>Active Sprint Progress</span>
              <span className="text-indigo-400 font-mono">{progressPercent}%</span>
            </div>
            <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-500 rounded-full"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <p className="text-[11px] text-slate-400 mt-2 text-right">
              {completedCount} of {totalActiveLessons} lessons completed
            </p>
          </div>
        </div>
      </div>

      {/* Section 1: Active 2-Week Window */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
          <h2 className="text-lg font-bold text-white tracking-tight">Active 2-Week Learning Sprint</h2>
          <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
            Detailed & In Progress
          </span>
        </div>

        <div className="space-y-6">
          {activeModules.map((module) => (
            <div
              key={module.id}
              className="glass-panel rounded-2xl p-5 sm:p-6 border border-slate-800/80 shadow-md"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 mb-4 border-b border-slate-800/60">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center font-bold text-xs">
                    W{module.target_week}
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-white">{module.title}</h3>
                    {module.description && <p className="text-xs text-slate-400 mt-0.5">{module.description}</p>}
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-400 font-medium">
                  <Clock className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Est. {module.estimated_hours}h</span>
                  <span>•</span>
                  <span>{module.lessons.length} lessons</span>
                </div>
              </div>

              {/* Lessons List */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                {module.lessons.map((lesson) => {
                  const isCompleted = lesson.status === "completed";
                  const isInProgress = lesson.status === "in_progress";
                  const isUpdating = updatingLessonId === lesson.id;

                  return (
                    <div
                      key={lesson.id}
                      onClick={() => onSelectLesson?.(lesson)}
                      className={`p-4 rounded-xl border transition-all cursor-pointer select-none group relative ${
                        isCompleted
                          ? "bg-emerald-950/20 border-emerald-500/30 text-slate-200"
                          : isInProgress
                          ? "bg-indigo-950/30 border-indigo-500/50 text-white shadow-lg shadow-indigo-950/50"
                          : "bg-slate-900/60 border-slate-800 hover:border-indigo-500/50 text-slate-300"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-2.5">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              if (!isUpdating) handleToggleLessonStatus(lesson);
                            }}
                            className="mt-0.5 text-slate-400 hover:text-white transition-colors"
                          >
                            {isCompleted ? (
                              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                            ) : isInProgress ? (
                              <div className="w-5 h-5 rounded-full border-2 border-indigo-400 border-t-transparent animate-spin" />
                            ) : (
                              <Circle className="w-5 h-5 text-slate-500 hover:text-slate-300" />
                            )}
                          </button>

                          <div>
                            <h4
                              className={`text-sm font-semibold leading-snug ${
                                isCompleted ? "line-through text-slate-400" : "text-white"
                              }`}
                            >
                              {lesson.title}
                            </h4>
                            <div className="flex items-center gap-2 mt-1.5 text-[11px] text-slate-400">
                              <span className="flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {lesson.duration_minutes} min
                              </span>
                              <span>•</span>
                              <span
                                className={`capitalize px-1.5 py-0.2 rounded font-medium ${
                                  isCompleted
                                    ? "text-emerald-400 bg-emerald-500/10"
                                    : isInProgress
                                    ? "text-indigo-400 bg-indigo-500/10"
                                    : "text-slate-400 bg-slate-800"
                                }`}
                              >
                                {lesson.status}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Objectives */}
                      {lesson.learning_objectives && lesson.learning_objectives.length > 0 && (
                        <div className="mt-3 pt-2.5 border-t border-slate-800/50 text-[11px] text-slate-400 space-y-1">
                          {lesson.learning_objectives.slice(0, 2).map((obj, i) => (
                            <div key={i} className="flex items-center gap-1.5 truncate">
                              <span className="w-1 h-1 rounded-full bg-indigo-400 flex-shrink-0" />
                              <span className="truncate">{obj}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Section 2: Future Roadmap (Plan Later) */}
      {futureModules.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Lock className="w-4 h-4 text-slate-500" />
            <h2 className="text-lg font-bold text-slate-300 tracking-tight">Future Roadmap (Plan Later)</h2>
            <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 font-medium">
              Adapts to demonstrated performance
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {futureModules.map((module) => (
              <div
                key={module.id}
                className="glass-panel rounded-2xl p-5 border border-slate-800/60 opacity-75 hover:opacity-100 transition-opacity relative group"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="px-2.5 py-1 rounded-lg bg-slate-800/80 text-xs font-semibold text-slate-400 border border-slate-700">
                    Week {module.target_week}
                  </div>
                  <Lock className="w-4 h-4 text-slate-500 group-hover:text-indigo-400 transition-colors" />
                </div>

                <h3 className="text-sm font-bold text-white mb-1">{module.title}</h3>
                <p className="text-xs text-slate-400 line-clamp-2">
                  {module.description || "Synthesized adaptive module."}
                </p>

                <div className="mt-4 pt-3 border-t border-slate-800/50 flex items-center justify-between text-[11px] text-slate-500">
                  <span>Est. {module.estimated_hours}h</span>
                  <span className="text-indigo-400/90 font-medium">Unlocks after Week 2</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
