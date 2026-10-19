import React, { useState, useEffect } from "react";
import {
  Calendar,
  Clock,
  CheckCircle2,
  Circle,
  Sparkles,
  RefreshCw,
  Repeat,
  BookOpen,
  CalendarCheck,
  AlertCircle
} from "lucide-react";
import { api, ScheduleItem, Roadmap } from "../api/client";

interface ScheduleViewProps {
  roadmap: Roadmap;
}

export const ScheduleView: React.FC<ScheduleViewProps> = ({ roadmap }) => {
  const [schedule, setSchedule] = useState<ScheduleItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [completingId, setCompletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchSchedule = async () => {
    setIsLoading(true);
    try {
      const data = await api.getSchedule(roadmap.id);
      setSchedule(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load study schedule");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSchedule();
  }, [roadmap.id]);

  const handleGenerateSchedule = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const updated = await api.generateSchedule(roadmap.id);
      setSchedule(updated);
    } catch (err: any) {
      setError(err.message || "Failed to generate schedule");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleToggleComplete = async (item: ScheduleItem) => {
    if (item.status === "completed") return; // Keep completed
    setCompletingId(item.id);
    try {
      await api.completeScheduleSession(item.id);
      setSchedule((prev) =>
        prev.map((s) => (s.id === item.id ? { ...s, status: "completed" } : s))
      );
    } catch (err: any) {
      setError(err.message || "Failed to update session status");
    } finally {
      setCompletingId(null);
    }
  };

  const completedSessions = schedule.filter((s) => s.status === "completed").length;
  const spacedSessions = schedule.filter((s) => s.session_type === "spaced_repetition").length;

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-3xl p-6 sm:p-8 bg-gradient-to-br from-slate-900 via-emerald-950/20 to-slate-900 border border-slate-800 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs uppercase font-bold tracking-wider px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                Spaced Repetition Calendar
              </span>
              <span className="text-xs text-slate-400">Paced by Daily Study Minutes</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Adaptive Study Schedule
            </h1>
            <p className="mt-2 text-sm text-slate-400 max-w-xl">
              Distributes your roadmap lessons across calendar dates respecting your daily learning capacity.
              When assessments identify weak areas, automated spaced repetition reviews are placed at +3 days and +7 days.
            </p>
          </div>

          {/* Action & Stats Card */}
          <div className="glass-panel p-5 rounded-2xl border border-slate-800 flex flex-col gap-3 w-full md:w-72 flex-shrink-0">
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-400">Completed Sessions:</span>
              <span className="text-emerald-400 font-mono font-bold">
                {completedSessions} / {schedule.length}
              </span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-400">Spaced Repetitions:</span>
              <span className="text-purple-400 font-mono font-bold">{spacedSessions}</span>
            </div>

            <button
              type="button"
              onClick={handleGenerateSchedule}
              disabled={isGenerating}
              className="mt-2 w-full py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-md shadow-emerald-600/20 transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isGenerating ? "animate-spin" : ""}`} />
              <span>{isGenerating ? "Synthesizing Calendar..." : "Recalculate Schedule"}</span>
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-xs font-bold hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Schedule Timeline */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 glass-panel rounded-3xl border border-slate-800">
          <div className="w-8 h-8 border-3 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
          <p className="text-xs text-slate-400 mt-3">Loading study calendar...</p>
        </div>
      ) : schedule.length === 0 ? (
        <div className="glass-panel rounded-3xl p-12 border border-slate-800 text-center max-w-lg mx-auto">
          <Calendar className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-bold text-white">No Schedule Generated Yet</h3>
          <p className="text-xs text-slate-400 mt-2 mb-6">
            Click the button above to generate a balanced study calendar based on your active roadmap and daily capacity.
          </p>
          <button
            onClick={handleGenerateSchedule}
            disabled={isGenerating}
            className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs inline-flex items-center gap-2"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Generate Initial Schedule</span>
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <CalendarCheck className="w-4 h-4 text-emerald-400" />
            <span>Scheduled Sessions ({schedule.length})</span>
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {schedule.map((item) => {
              const isCompleted = item.status === "completed";
              const isSpaced = item.session_type === "spaced_repetition";
              const isUpdating = completingId === item.id;

              return (
                <div
                  key={item.id}
                  className={`glass-panel p-5 rounded-2xl border transition-all flex flex-col justify-between space-y-3 ${
                    isCompleted
                      ? "bg-emerald-950/10 border-emerald-500/20 opacity-75"
                      : isSpaced
                      ? "bg-purple-950/20 border-purple-500/30 shadow-md shadow-purple-950/20"
                      : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <span className="text-[11px] font-mono text-slate-400 flex items-center gap-1.5">
                        <Calendar className="w-3 h-3 text-emerald-400" />
                        {item.scheduled_date}
                      </span>

                      <span
                        className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                          isSpaced
                            ? "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                            : "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                        }`}
                      >
                        {isSpaced ? "Spaced Review" : "Lesson"}
                      </span>
                    </div>

                    <h4
                      className={`text-sm font-bold leading-snug ${
                        isCompleted ? "line-through text-slate-400" : "text-white"
                      }`}
                    >
                      {item.lesson_title || "Lesson Session"}
                    </h4>
                  </div>

                  <div className="pt-3 border-t border-slate-800/60 flex items-center justify-between">
                    <span className="text-xs text-slate-400 flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-500" />
                      {item.estimated_minutes > 0 ? `${item.estimated_minutes} min` : "Scheduled"}
                    </span>

                    <button
                      type="button"
                      onClick={() => handleToggleComplete(item)}
                      disabled={isCompleted || isUpdating}
                      className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
                        isCompleted
                          ? "bg-emerald-500/10 text-emerald-400 cursor-default"
                          : "bg-slate-800 hover:bg-slate-700 text-slate-200"
                      }`}
                    >
                      {isCompleted ? (
                        <>
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                          <span>Done</span>
                        </>
                      ) : (
                        <>
                          <Circle className="w-3.5 h-3.5 text-slate-400" />
                          <span>Mark Done</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
