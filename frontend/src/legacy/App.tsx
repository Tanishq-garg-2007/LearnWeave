import React, { useEffect, useState } from "react";
import { Navbar, NavTab } from "./components/Navbar";
import { GoalIntakeModal } from "./components/GoalIntakeModal";
import { AuthModal } from "./components/AuthModal";
import { RoadmapView } from "./components/RoadmapView";
import { NotesView } from "./components/NotesView";
import { ScheduleView } from "./components/ScheduleView";
import { CommunityView } from "./components/CommunityView";
import { LearningCycleModal } from "./components/LearningCycleModal";
import {
  api,
  UserProfile,
  Roadmap,
  Lesson,
  getAuthToken,
  clearAuthToken,
  ApiError,
  UNAUTHORIZED_EVENT,
  CreateGoalPayload
} from "./api/client";
import { Sparkles, BookOpen, Compass, ShieldCheck, Zap, Layers, RefreshCw } from "lucide-react";

export const App: React.FC = () => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [activeRoadmap, setActiveRoadmap] = useState<Roadmap | null>(null);
  const [activeTab, setActiveTab] = useState<NavTab>("roadmap");
  const [selectedLesson, setSelectedLesson] = useState<Lesson | null>(null);
  const [isGoalModalOpen, setIsGoalModalOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isLoadingRoadmap, setIsLoadingRoadmap] = useState(false);
  const [isCreatingGoal, setIsCreatingGoal] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchUserData = async () => {
    const token = getAuthToken();
    if (!token) return;

    try {
      const profile = await api.getMe();
      setUser(profile);
      fetchActiveRoadmap();
    } catch (err) {
      // Only a rejected token ends the session. A network blip or a 5xx must not log the user out.
      if (err instanceof ApiError && err.status === 401) {
        clearAuthToken();
        setUser(null);
      } else {
        console.error("Could not load profile:", err);
        setError("Could not reach the server. Your session is kept; please retry in a moment.");
      }
    }
  };

  const fetchActiveRoadmap = async () => {
    setIsLoadingRoadmap(true);
    try {
      const roadmap = await api.getActiveRoadmap();
      setActiveRoadmap(roadmap);
      setError(null);
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 404) {
        setActiveRoadmap(null); // no active roadmap yet
      } else if (!(err instanceof ApiError && err.status === 401)) {
        setError(err?.message || "Failed to load your roadmap");
      }
    } finally {
      setIsLoadingRoadmap(false);
    }
  };

  useEffect(() => {
    fetchUserData();
  }, []);

  // Any authenticated call that returns 401 (expired/revoked token) logs the user out cleanly.
  useEffect(() => {
    const onUnauthorized = () => {
      clearAuthToken();
      setUser(null);
      setActiveRoadmap(null);
      setSelectedLesson(null);
      setError("Your session expired. Please sign in again.");
    };
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, []);

  const handleCreateGoal = async (payload: CreateGoalPayload) => {
    setIsCreatingGoal(true);
    setError(null);
    try {
      const createdRoadmap = await api.createGoalAndRoadmap(payload);
      setActiveRoadmap(createdRoadmap);
      setIsGoalModalOpen(false);
      setActiveTab("roadmap");
      fetchUserData();
    } catch (err: any) {
      setError(err.message || "Failed to synthesize roadmap");
    } finally {
      setIsCreatingGoal(false);
    }
  };

  const handleLogout = () => {
    clearAuthToken();
    setUser(null);
    setActiveRoadmap(null);
    setActiveTab("roadmap");
    setSelectedLesson(null);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      <Navbar
        user={user}
        activeTab={activeTab}
        onTabChange={(tab) => setActiveTab(tab)}
        onOpenGoalModal={() => {
          if (!user) {
            setIsAuthModalOpen(true);
          } else {
            setIsGoalModalOpen(true);
          }
        }}
        onOpenAuthModal={() => setIsAuthModalOpen(true)}
        onLogout={handleLogout}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-6 p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-xs font-bold hover:underline">
              Dismiss
            </button>
          </div>
        )}

        {/* Tab-driven View Rendering */}
        {activeTab === "notes" ? (
          <NotesView onRefreshRoadmap={fetchActiveRoadmap} />
        ) : activeTab === "schedule" ? (
          activeRoadmap ? (
            <ScheduleView roadmap={activeRoadmap} />
          ) : (
            <div className="glass-panel rounded-3xl p-12 border border-slate-800 text-center max-w-lg mx-auto">
              <Layers className="w-12 h-12 text-slate-600 mx-auto mb-3" />
              <h3 className="text-base font-bold text-white">No Active Roadmap</h3>
              <p className="text-xs text-slate-400 mt-2 mb-6">
                Please set a learning goal to generate your roadmap and schedule.
              </p>
              <button
                onClick={() => setIsGoalModalOpen(true)}
                className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs inline-flex items-center gap-2"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Create Learning Goal</span>
              </button>
            </div>
          )
        ) : activeTab === "community" ? (
          <CommunityView onNoteImported={fetchUserData} />
        ) : (
          /* Roadmap Tab */
          isLoadingRoadmap ? (
            <div className="flex flex-col items-center justify-center py-24 space-y-4">
              <div className="w-10 h-10 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
              <p className="text-sm text-slate-400">Loading your persistent learning state...</p>
            </div>
          ) : activeRoadmap ? (
            <RoadmapView
              roadmap={activeRoadmap}
              onRefresh={fetchActiveRoadmap}
              onSelectLesson={(lesson) => setSelectedLesson(lesson)}
            />
          ) : (
            /* Welcome / Empty State */
            <div className="relative overflow-hidden rounded-3xl p-8 sm:p-14 bg-gradient-to-br from-slate-900 via-indigo-950/20 to-slate-900 border border-slate-800/80 shadow-2xl text-center max-w-3xl mx-auto my-8">
              <div className="w-16 h-16 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 flex items-center justify-center mx-auto mb-6 shadow-xl shadow-indigo-600/10">
                <Compass className="w-8 h-8 text-indigo-400 animate-pulse" />
              </div>

              <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
                A Personal AI Companion for Deep, Long-Term Mastery
              </h2>
              <p className="mt-4 text-base text-slate-400 leading-relaxed max-w-xl mx-auto">
                LearnWeave replaces ephemeral chatbot queries with stateful, multi-week learning journeys.
                Set a goal to receive a structured 2-week active sprint, grounded lesson explanations, and adaptive future milestones.
              </p>

              <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
                <button
                  onClick={() => {
                    if (!user) {
                      setIsAuthModalOpen(true);
                    } else {
                      setIsGoalModalOpen(true);
                    }
                  }}
                  className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-3.5 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-purple-600 text-white font-bold text-sm shadow-xl shadow-indigo-600/30 transition-all hover:scale-105"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>Begin Your Learning Journey</span>
                </button>
              </div>

              {/* Feature Pills */}
              <div className="mt-12 pt-8 border-t border-slate-800/60 grid grid-cols-1 sm:grid-cols-3 gap-6 text-left">
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-slate-800 text-indigo-400">
                    <Layers className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white uppercase tracking-wider">2-Week Sprint Focus</h4>
                    <p className="text-xs text-slate-400 mt-1">Detailed near-term lessons, future weeks adapt as you master concepts.</p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-slate-800 text-emerald-400">
                    <ShieldCheck className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white uppercase tracking-wider">Private Workspaces</h4>
                    <p className="text-xs text-slate-400 mt-1">Your notes, embeddings, and progress remain strictly private to you.</p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-slate-800 text-purple-400">
                    <Zap className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white uppercase tracking-wider">Deterministic State</h4>
                    <p className="text-xs text-slate-400 mt-1">PostgreSQL stores authoritative progress, avoiding memory drift.</p>
                  </div>
                </div>
              </div>
            </div>
          )
        )}
      </main>

      {/* Modals */}
      <GoalIntakeModal
        isOpen={isGoalModalOpen}
        onClose={() => setIsGoalModalOpen(false)}
        onSubmit={handleCreateGoal}
        isLoading={isCreatingGoal}
      />

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onSuccess={fetchUserData}
      />

      <LearningCycleModal
        lesson={selectedLesson}
        isOpen={selectedLesson !== null}
        onClose={() => setSelectedLesson(null)}
        onLessonCompleted={() => {
          fetchActiveRoadmap();
          fetchUserData();
        }}
      />
    </div>
  );
};
