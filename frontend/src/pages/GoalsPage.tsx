import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api";
import type { GoalResponse, RoadmapDetailResponse } from "@/api/types";
import { GoalIntakeModal } from "@/features/goals/GoalIntakeModal";
import { Target, Plus, Sparkles, Clock, Calendar, ArrowRight, RotateCw } from "lucide-react";

export default function GoalsPage(): JSX.Element {
  const [goals, setGoals] = useState<GoalResponse[]>([]);
  const [activeRoadmap, setActiveRoadmap] = useState<RoadmapDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [roadmapData, goalsList] = await Promise.all([
        api.getActiveRoadmap().catch(() => null),
        api.listGoals().catch(() => []),
      ]);
      setActiveRoadmap(roadmapData);
      setGoals(goalsList || []);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="py-6 sm:py-10 px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto space-y-8 text-left animate-in fade-in duration-200">
      <div className="rounded-3xl p-6 sm:p-8 bg-white/75 border border-white/85 shadow-glass backdrop-blur-xl flex flex-col sm:flex-row sm:items-center justify-between gap-6">
        <div className="space-y-1">
          <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-cyan-100 text-cyan-800">
            Learning Objectives
          </span>
          <h1 className="text-2xl sm:text-3xl font-display text-ink font-semibold">
            My Learning Goals
          </h1>
          <p className="text-xs text-muted">
            Track your target proficiency goals and active sprints.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#252229] hover:bg-[#151318] text-white text-xs font-semibold shadow-md active:scale-95 transition-all self-start sm:self-auto"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Goal</span>
        </button>
      </div>

      {isLoading ? (
        <div className="py-20 text-center text-xs text-muted">
          <RotateCw className="w-6 h-6 animate-spin mx-auto mb-2 text-muted" />
          Loading your goals...
        </div>
      ) : activeRoadmap ? (
        <div className="space-y-4">
          <h2 className="text-base font-bold text-ink">Active Learning Goal</h2>
          <div className="rounded-3xl p-6 bg-white/85 border border-white/90 shadow-glass space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-cyan-100 text-cyan-800">
                  Sprint Roadmap v{activeRoadmap.version}
                </span>
                <h3 className="text-lg font-bold text-ink mt-1">{activeRoadmap.title}</h3>
              </div>
              <Link
                to="/roadmap"
                className="inline-flex items-center gap-1.5 px-5 py-2 rounded-full bg-[#252229] text-white text-xs font-semibold shadow-md self-start sm:self-auto"
              >
                <span>View Roadmap</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="flex items-center gap-4 text-xs text-muted pt-2 border-t border-surface-border">
              <span>{activeRoadmap.total_modules} Modules Planned</span>
              <span>•</span>
              <span>{activeRoadmap.total_lessons} Lessons Total</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-12 rounded-3xl bg-white/70 border border-white/80 shadow-glass text-center space-y-3">
          <Target className="w-10 h-10 text-muted mx-auto" />
          <p className="text-sm font-bold text-ink">No goals created yet</p>
          <p className="text-xs text-muted">Set a goal to synthesize your personalized learning roadmap.</p>
          <button
            type="button"
            onClick={() => setIsModalOpen(true)}
            className="px-6 py-2.5 rounded-full bg-[#252229] text-white text-xs font-semibold shadow-md"
          >
            Create First Goal
          </button>
        </div>
      )}

      {/* Goal Intake Modal */}
      <GoalIntakeModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={() => loadData()}
      />
    </div>
  );
}
