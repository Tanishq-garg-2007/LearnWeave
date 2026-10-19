import React, { useState } from "react";
import { X, Sparkles, Clock, Target, BookOpen, Layers } from "lucide-react";
import { CreateGoalPayload } from "../api/client";

interface GoalIntakeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (payload: CreateGoalPayload) => Promise<void>;
  isLoading: boolean;
}

export const GoalIntakeModal: React.FC<GoalIntakeModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  isLoading,
}) => {
  const [subject, setSubject] = useState("");
  const [currentLevel, setCurrentLevel] = useState("beginner");
  const [targetLevel, setTargetLevel] = useState("intermediate");
  const [durationWeeks, setDurationWeeks] = useState(4);
  const [hoursPerWeek, setHoursPerWeek] = useState(6);
  const [style, setStyle] = useState("practical code examples with visual analogies");
  const [objectives, setObjectives] = useState("");

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!subject.trim()) return;

    const specific_objectives = objectives
      .split("\n")
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    await onSubmit({
      subject: subject.trim(),
      current_level: currentLevel,
      target_level: targetLevel,
      total_duration_weeks: Number(durationWeeks),
      hours_per_week: Number(hoursPerWeek),
      preferred_style: style,
      specific_objectives,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-6 sm:p-8 max-h-[90vh] overflow-y-auto">
        <button
          onClick={onClose}
          disabled={isLoading}
          className="absolute top-5 right-5 text-slate-400 hover:text-white p-1 rounded-lg transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Design Your Learning Goal</h2>
            <p className="text-xs text-slate-400">RoadmapPlanningAgent will synthesize a personalized 2-week active plan</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Subject */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Subject or Skill *
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Operating Systems, Distributed Consensus, Neural Networks"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-sm transition-all"
            />
          </div>

          {/* Levels Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                Current Proficiency
              </label>
              <select
                value={currentLevel}
                onChange={(e) => setCurrentLevel(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-indigo-500"
              >
                <option value="beginner">Beginner (No prior background)</option>
                <option value="intermediate">Intermediate (Foundational concepts known)</option>
                <option value="advanced">Advanced (Hands-on practitioner)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                Target Mastery Level
              </label>
              <select
                value={targetLevel}
                onChange={(e) => setTargetLevel(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-indigo-500"
              >
                <option value="intermediate">Intermediate (Comfortable building projects)</option>
                <option value="advanced">Advanced (Deep architectural mastery)</option>
                <option value="mastery">Mastery (Expert troubleshooting & theory)</option>
              </select>
            </div>
          </div>

          {/* Time & Duration */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-indigo-400" />
                Duration ({durationWeeks} Weeks)
              </label>
              <input
                type="range"
                min="2"
                max="12"
                value={durationWeeks}
                onChange={(e) => setDurationWeeks(Number(e.target.value))}
                className="w-full accent-indigo-500"
              />
              <div className="flex justify-between text-[11px] text-slate-400 mt-1">
                <span>2 weeks (Crash)</span>
                <span>4 weeks</span>
                <span>12 weeks (Deep)</span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5 flex items-center gap-1.5">
                <Target className="w-3.5 h-3.5 text-indigo-400" />
                Weekly Commitment ({hoursPerWeek} Hours/Week)
              </label>
              <input
                type="range"
                min="2"
                max="20"
                value={hoursPerWeek}
                onChange={(e) => setHoursPerWeek(Number(e.target.value))}
                className="w-full accent-indigo-500"
              />
              <div className="flex justify-between text-[11px] text-slate-400 mt-1">
                <span>2 hrs (Casual)</span>
                <span>6 hrs (Balanced)</span>
                <span>20 hrs (Intensive)</span>
              </div>
            </div>
          </div>

          {/* Explanation Style */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Preferred Learning Style
            </label>
            <input
              type="text"
              value={style}
              onChange={(e) => setStyle(e.target.value)}
              placeholder="e.g. intuitive analogies, step-by-step code, first-principles derivations"
              className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 text-sm"
            />
          </div>

          {/* Objectives */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Specific Objectives (One per line)
            </label>
            <textarea
              rows={3}
              value={objectives}
              onChange={(e) => setObjectives(e.target.value)}
              placeholder="e.g. Master CPU scheduling algorithms&#10;Understand virtual memory paging&#10;Implement mutex and semaphore locks in C"
              className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 text-sm font-mono"
            />
          </div>

          {/* Submit */}
          <div className="pt-2 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="px-4 py-2 rounded-xl text-slate-400 hover:text-white text-sm font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Synthesizing Curriculum...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Generate Roadmap</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
