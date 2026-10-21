import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/api";
import type { GoalCreateRequest } from "@/api/types";
import { Sparkles, Target, ArrowRight, RotateCw, AlertCircle } from "lucide-react";
import { useToast } from "@/components/ui/Toast";

export default function OnboardingPage(): JSX.Element {
  const [subject, setSubject] = useState("");
  const [currentLevel, setCurrentLevel] = useState("beginner");
  const [targetLevel, setTargetLevel] = useState("intermediate");
  const [durationWeeks, setDurationWeeks] = useState(4);
  const [hoursPerWeek, setHoursPerWeek] = useState(6);
  const [style, setStyle] = useState("practical code examples with visual analogies");
  const [objectives, setObjectives] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const navigate = useNavigate();
  const toast = useToast();

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
      await api.createGoalAndRoadmap(payload);
      toast.success("Goal created! Your personalized active sprint roadmap is synthesized.");
      navigate("/roadmap");
    } catch (err: any) {
      setError(err?.message || "Failed to create goal and synthesize roadmap.");
      toast.error(err?.message || "Failed to create goal.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="py-8 sm:py-14 px-4 sm:px-6 lg:px-8 max-w-2xl mx-auto space-y-6 text-left animate-in fade-in duration-200">
      <div className="rounded-3xl p-6 sm:p-10 bg-white/55 border border-white/85 shadow-[0_16px_40px_-10px_rgba(40,30,60,0.08)] ring-1 ring-inset ring-white/80 backdrop-blur-2xl space-y-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-[#252229] text-white flex items-center justify-center shadow-soft">
            <Sparkles className="w-6 h-6 text-cyan-300" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-display text-ink font-bold">
              Design Your Learning Goal
            </h1>
            <p className="text-xs text-muted">
              LearnWeave's agentic planner will synthesize a personalized 2-week active sprint.
            </p>
          </div>
        </div>

        {error && (
          <div className="p-3.5 rounded-2xl bg-danger/10 border border-danger/20 text-xs text-danger font-medium flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
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
              className="w-full px-4 py-2.5 rounded-2xl bg-white/70 border border-white/80 ring-1 ring-inset ring-white/70 text-ink text-xs focus:outline-none focus:ring-2 focus:ring-focus focus:bg-white"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-text mb-1">
                Current Proficiency
              </label>
              <select
                value={currentLevel}
                onChange={(e) => setCurrentLevel(e.target.value)}
                className="w-full px-4 py-2.5 rounded-2xl bg-white/70 border border-white/80 ring-1 ring-inset ring-white/70 text-ink text-xs focus:outline-none focus:ring-2 focus:ring-focus focus:bg-white"
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
                className="w-full px-4 py-2.5 rounded-2xl bg-white/70 border border-white/80 ring-1 ring-inset ring-white/70 text-ink text-xs focus:outline-none focus:ring-2 focus:ring-focus focus:bg-white"
              >
                <option value="intermediate">Intermediate (Competent application)</option>
                <option value="advanced">Advanced (Deep theoretical mastery)</option>
                <option value="expert">Expert (Research & architecture level)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-text mb-1">
                Goal Duration (Weeks)
              </label>
              <input
                type="number"
                min={1}
                max={24}
                value={durationWeeks}
                onChange={(e) => setDurationWeeks(Number(e.target.value))}
                className="w-full px-4 py-2.5 rounded-2xl bg-white/70 border border-white/80 ring-1 ring-inset ring-white/70 text-ink text-xs focus:outline-none focus:ring-2 focus:ring-focus focus:bg-white"
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
                className="w-full px-4 py-2.5 rounded-2xl bg-white/70 border border-white/80 ring-1 ring-inset ring-white/70 text-ink text-xs focus:outline-none focus:ring-2 focus:ring-focus focus:bg-white"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-text mb-1">
              Preferred Learning Style
            </label>
            <input
              type="text"
              value={style}
              onChange={(e) => setStyle(e.target.value)}
              placeholder="e.g. practical code examples, visual analogies, step-by-step proofs"
              className="w-full px-4 py-2.5 rounded-2xl bg-white/70 border border-white/80 ring-1 ring-inset ring-white/70 text-ink text-xs focus:outline-none focus:ring-2 focus:ring-focus focus:bg-white"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-text mb-1">
              Specific Learning Objectives (One per line)
            </label>
            <textarea
              rows={3}
              value={objectives}
              onChange={(e) => setObjectives(e.target.value)}
              placeholder="e.g.&#10;Implement virtual memory page replacement&#10;Master Raft consensus protocol&#10;Prepare for upcoming engineering interview"
              className="w-full px-4 py-2 rounded-2xl bg-white/70 border border-white/80 ring-1 ring-inset ring-white/70 text-ink text-xs placeholder:text-muted/60 focus:outline-none focus:ring-2 focus:ring-focus focus:bg-white"
            />
          </div>

          <div className="pt-4 flex justify-end">
            <button
              type="submit"
              disabled={isSubmitting || !subject.trim()}
              className="inline-flex items-center gap-2 px-8 py-3 rounded-full bg-[#252229] hover:bg-[#151318] disabled:opacity-50 text-white text-xs font-semibold shadow-md active:scale-95 transition-all"
            >
              {isSubmitting ? (
                <>
                  <RotateCw className="w-4 h-4 animate-spin" />
                  <span>Synthesizing Active Sprint Roadmap...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 text-cyan-300" />
                  <span>Synthesize Roadmap</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
