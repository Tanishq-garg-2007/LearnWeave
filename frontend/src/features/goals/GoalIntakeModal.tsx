import React, { useState } from "react";
import { X, Sparkles, Target, Clock, BookOpen, Layers } from "lucide-react";
import { api } from "@/api";
import type { GoalCreateRequest, RoadmapDetailResponse } from "@/api/types";
import { useToast } from "@/components/ui/Toast";

interface GoalIntakeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (roadmap: RoadmapDetailResponse) => void;
}

export function GoalIntakeModal({
  isOpen,
  onClose,
  onSuccess,
}: GoalIntakeModalProps): JSX.Element | null {
  const [subject, setSubject] = useState("");
  const [currentLevel, setCurrentLevel] = useState("beginner");
  const [targetLevel, setTargetLevel] = useState("intermediate");
  const [durationWeeks, setDurationWeeks] = useState(4);
  const [hoursPerWeek, setHoursPerWeek] = useState(6);
  const [style, setStyle] = useState("practical code examples with visual analogies");
  const [objectives, setObjectives] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toast = useToast();

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!subject.trim()) return;

    setIsSubmitting(true);
    setError(null);

    const specific_objectives = objectives
      .split("\n")
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    const payload: GoalCreateRequest = {
      subject: subject.trim(),
      current_level: currentLevel,
      target_level: targetLevel,
      total_duration_weeks: Number(durationWeeks),
      hours_per_week: Number(hoursPerWeek),
      preferred_style: style,
      specific_objectives,
    };

    try {
      const roadmap = await api.createGoalAndRoadmap(payload);
      toast.success("Goal set! Your 2-week active sprint roadmap is synthesized.");
      onSuccess(roadmap);
      onClose();
    } catch (err: any) {
      setError(err?.message || "Failed to synthesize roadmap. Please retry.");
      toast.error(err?.message || "Failed to synthesize roadmap.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl bg-white/95 border border-white/80 shadow-2xl rounded-3xl p-6 sm:p-8 max-h-[92vh] overflow-y-auto">
        <button
          onClick={onClose}
          disabled={isSubmitting}
          className="absolute top-5 right-5 text-muted hover:text-ink p-1 rounded-full hover:bg-black/5 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-6">
          <div className="w-11 h-11 rounded-2xl bg-[#252229] text-white flex items-center justify-center shadow-soft">
            <Sparkles className="w-5 h-5 text-cyan-300" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-ink">Design Your Learning Goal</h2>
            <p className="text-xs text-muted">
              RoadmapPlanningAgent will synthesize a personalized 2-week active learning sprint.
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-2xl bg-danger/10 border border-danger/20 text-xs text-danger font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Subject */}
          <div>
            <label className="block text-xs font-semibold text-text mb-1">
              Subject or Skill to Master *
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Operating Systems, Distributed Systems, Graph Neural Networks"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full px-4 py-2.5 rounded-2xl bg-white border border-surface-border text-ink placeholder:text-muted/60 text-xs focus:outline-none focus:ring-2 focus:ring-focus transition-all"
            />
          </div>

          {/* Proficiency Levels */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-text mb-1">
                Current Proficiency
              </label>
              <select
                value={currentLevel}
                onChange={(e) => setCurrentLevel(e.target.value)}
                className="w-full px-4 py-2.5 rounded-2xl bg-white border border-surface-border text-ink text-xs focus:outline-none focus:ring-2 focus:ring-focus"
              >
                <option value="beginner">Beginner (No prior background)</option>
                <option value="intermediate">Intermediate (Foundational concepts known)</option>
                <option value="advanced">Advanced (Hands-on practitioner)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-text mb-1">
                Target Mastery Goal
              </label>
              <select
                value={targetLevel}
                onChange={(e) => setTargetLevel(e.target.value)}
                className="w-full px-4 py-2.5 rounded-2xl bg-white border border-surface-border text-ink text-xs focus:outline-none focus:ring-2 focus:ring-focus"
              >
                <option value="intermediate">Intermediate (Competent application)</option>
                <option value="advanced">Advanced (Deep theoretical & systems mastery)</option>
                <option value="expert">Expert (Research & architecture level)</option>
              </select>
            </div>
          </div>

          {/* Time & Pacing */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-text mb-1">
                Total Goal Duration (Weeks)
              </label>
              <input
                type="number"
                min={1}
                max={24}
                value={durationWeeks}
                onChange={(e) => setDurationWeeks(Number(e.target.value))}
                className="w-full px-4 py-2.5 rounded-2xl bg-white border border-surface-border text-ink text-xs focus:outline-none focus:ring-2 focus:ring-focus"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-text mb-1">
                Study Hours Per Week
              </label>
              <input
                type="number"
                min={1}
                max={40}
                value={hoursPerWeek}
                onChange={(e) => setHoursPerWeek(Number(e.target.value))}
                className="w-full px-4 py-2.5 rounded-2xl bg-white border border-surface-border text-ink text-xs focus:outline-none focus:ring-2 focus:ring-focus"
              />
            </div>
          </div>

          {/* Preferred Style */}
          <div>
            <label className="block text-xs font-semibold text-text mb-1">
              Preferred Learning Style
            </label>
            <input
              type="text"
              value={style}
              onChange={(e) => setStyle(e.target.value)}
              placeholder="e.g. practical code examples, visual analogies, rigorous mathematical proofs"
              className="w-full px-4 py-2.5 rounded-2xl bg-white border border-surface-border text-ink text-xs focus:outline-none focus:ring-2 focus:ring-focus"
            />
          </div>

          {/* Objectives */}
          <div>
            <label className="block text-xs font-semibold text-text mb-1">
              Specific Objectives (One per line)
            </label>
            <textarea
              rows={3}
              value={objectives}
              onChange={(e) => setObjectives(e.target.value)}
              placeholder="e.g.&#10;Implement virtual memory page replacement&#10;Understand Raft consensus leader election&#10;Pass upcoming technical interview"
              className="w-full px-4 py-2 rounded-2xl bg-white border border-surface-border text-ink text-xs placeholder:text-muted/60 focus:outline-none focus:ring-2 focus:ring-focus"
            />
          </div>

          <div className="pt-3 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-5 py-2.5 rounded-full bg-black/5 hover:bg-black/10 text-muted hover:text-ink text-xs font-semibold transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !subject.trim()}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-full bg-[#252229] hover:bg-[#151318] disabled:opacity-50 text-white text-xs font-semibold shadow-md transition-all active:scale-95"
            >
              {isSubmitting ? (
                <>
                  <span className="h-3 w-3 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                  <span>Synthesizing Sprint...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5 text-cyan-300" />
                  <span>Generate Active Roadmap</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default GoalIntakeModal;
