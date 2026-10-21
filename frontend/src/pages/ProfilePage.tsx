import React, { useState } from "react";
import { useAuth } from "@/features/auth/AuthProvider";
import { api } from "@/api";
import { GlassCard } from "@/components/ui/GlassCard";
import { useToast } from "@/components/ui/Toast";
import {
  User,
  Award,
  BookOpen,
  BrainCircuit,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  RotateCw,
  Sparkles,
} from "lucide-react";

export default function ProfilePage(): JSX.Element {
  const { user } = useAuth();
  const [dailyMinutes, setDailyMinutes] = useState(
    user?.profile?.preferences?.daily_minutes || 45
  );
  const [depth, setDepth] = useState(
    user?.profile?.preferences?.explanation_depth || "balanced"
  );
  const [analogies, setAnalogies] = useState(
    user?.profile?.preferences?.analogies_preferred ?? true
  );
  const [isSaving, setIsSaving] = useState(false);

  const toast = useToast();

  const handleSavePreferences = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      await api.updateProfile({
        daily_minutes: Number(dailyMinutes),
        explanation_depth: depth,
        analogies_preferred: analogies,
      });
      toast.success("Learner preferences updated successfully!");
    } catch (err: any) {
      toast.error(err?.message || "Failed to update preferences.");
    } finally {
      setIsSaving(false);
    }
  };

  const topicMastery = user?.profile?.topic_mastery || {};
  const weakAreas = user?.profile?.weak_areas || [];
  const completedLessons = user?.profile?.completed_lessons || [];

  return (
    <div className="py-6 sm:py-10 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto space-y-8 text-left animate-in fade-in duration-200">
      {/* Header Banner */}
      <div className="rounded-3xl p-6 sm:p-8 bg-white/75 border border-white/85 shadow-glass backdrop-blur-xl flex flex-col sm:flex-row sm:items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-3xl bg-[#252229] text-white flex items-center justify-center font-bold text-2xl shadow-soft">
            {(user?.full_name || user?.email || "S")[0].toUpperCase()}
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-ink">
              {user?.full_name || "Learner Profile"}
            </h1>
            <p className="text-xs text-muted">{user?.email}</p>
            {user?.workspace_id && (
              <p className="text-[10px] font-mono text-muted/70 mt-0.5">
                Workspace: {user.workspace_id}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="p-3 px-4 rounded-2xl bg-white border border-surface-border text-center shadow-xs">
            <p className="text-xl font-bold font-mono text-emerald-600">
              {completedLessons.length}
            </p>
            <p className="text-[10px] text-muted">Completed Lessons</p>
          </div>
        </div>
      </div>

      {/* Mastery & Weak Areas Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Topic Mastery */}
        <div className="p-6 rounded-3xl bg-white/85 border border-white/90 shadow-glass space-y-4">
          <div className="flex items-center gap-2">
            <Award className="w-4 h-4 text-cyan-600" />
            <h2 className="text-sm font-bold text-ink">Evaluated Topic Mastery</h2>
          </div>

          {Object.keys(topicMastery).length === 0 ? (
            <p className="text-xs text-muted py-6 text-center">
              No topic assessments recorded yet. Complete quiz evaluations to calibrate your topic mastery scores.
            </p>
          ) : (
            <div className="space-y-3">
              {Object.entries(topicMastery).map(([topic, score]) => (
                <div key={topic} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-semibold text-ink">{topic}</span>
                    <span className="font-mono text-muted">{Math.round(score * 100)}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-black/5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-cyan-400 to-blue-500 rounded-full"
                      style={{ width: `${Math.round(score * 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Identified Weak Areas */}
        <div className="p-6 rounded-3xl bg-white/85 border border-white/90 shadow-glass space-y-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <h2 className="text-sm font-bold text-ink">Identified Weak Areas</h2>
          </div>

          {weakAreas.length === 0 ? (
            <div className="p-6 rounded-2xl bg-emerald-50/70 border border-emerald-200 text-center text-xs text-emerald-800 space-y-1">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 mx-auto mb-1" />
              <p className="font-semibold">No critical weak areas detected</p>
              <p className="text-[11px] text-muted">
                Your formative quiz evaluations have met the 70% threshold.
              </p>
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {weakAreas.map((area, idx) => (
                <span
                  key={idx}
                  className="px-3 py-1 rounded-full bg-rose-50 border border-rose-200 text-xs font-semibold text-rose-800"
                >
                  {area}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Preferences Form */}
      <div className="p-6 sm:p-8 rounded-3xl bg-white/85 border border-white/90 shadow-glass space-y-5">
        <div className="flex items-center gap-2">
          <Sliders className="w-4 h-4 text-violet" />
          <h2 className="text-base font-bold text-ink">Study Preferences</h2>
        </div>

        <form onSubmit={handleSavePreferences} className="space-y-4 max-w-xl">
          <div>
            <label className="block text-xs font-semibold text-text mb-1">
              Target Daily Study Minutes
            </label>
            <input
              type="number"
              min={15}
              max={180}
              value={dailyMinutes}
              onChange={(e) => setDailyMinutes(Number(e.target.value))}
              className="w-full px-4 py-2.5 rounded-2xl bg-white border border-surface-border text-ink text-xs focus:outline-none focus:ring-2 focus:ring-focus"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-text mb-1">
              Lesson Explanation Depth
            </label>
            <select
              value={depth}
              onChange={(e) => setDepth(e.target.value)}
              className="w-full px-4 py-2.5 rounded-2xl bg-white border border-surface-border text-ink text-xs focus:outline-none focus:ring-2 focus:ring-focus"
            >
              <option value="concise">Concise & Practical</option>
              <option value="balanced">Balanced with Examples</option>
              <option value="rigorous">Deep Academic & Systems Rigor</option>
            </select>
          </div>

          <div className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id="analogies"
              checked={analogies}
              onChange={(e) => setAnalogies(e.target.checked)}
              className="w-4 h-4 rounded text-ink focus:ring-focus"
            />
            <label htmlFor="analogies" className="text-xs font-medium text-text cursor-pointer">
              Include visual and real-world engineering analogies in generated lessons
            </label>
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={isSaving}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-full bg-[#252229] hover:bg-[#151318] text-white text-xs font-semibold shadow-md active:scale-95 transition-all"
            >
              {isSaving ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : null}
              <span>Save Preferences</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
