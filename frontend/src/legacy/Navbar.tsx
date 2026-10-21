import React from "react";
import {
  Compass,
  BookOpen,
  User,
  LogOut,
  Sparkles,
  Layers,
  FileText,
  Calendar,
  Globe
} from "lucide-react";
import { UserProfile } from "../api/client";

export type NavTab = "roadmap" | "notes" | "schedule" | "community";

interface NavbarProps {
  user: UserProfile | null;
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  onOpenGoalModal: () => void;
  onOpenAuthModal: () => void;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  user,
  activeTab,
  onTabChange,
  onOpenGoalModal,
  onOpenAuthModal,
  onLogout,
}) => {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Compass className="w-5 h-5 text-white animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-white via-slate-100 to-indigo-200 bg-clip-text text-transparent">
                LearnWeave
              </span>
              <span className="text-xs uppercase tracking-widest font-bold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                AI Agentic
              </span>
            </div>
            <p className="text-[11px] text-slate-400 -mt-0.5">Continuous Adaptive Learning</p>
          </div>
        </div>

        {/* Center Nav Links (When logged in) */}
        {user && (
          <nav className="hidden md:flex items-center gap-1 bg-slate-900/80 p-1 rounded-xl border border-slate-800/80">
            <button
              onClick={() => onTabChange("roadmap")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                activeTab === "roadmap"
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Roadmap</span>
            </button>

            <button
              onClick={() => onTabChange("notes")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                activeTab === "notes"
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Notes & RAG</span>
            </button>

            <button
              onClick={() => onTabChange("schedule")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                activeTab === "schedule"
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              }`}
            >
              <Calendar className="w-3.5 h-3.5" />
              <span>Schedule</span>
            </button>

            <button
              onClick={() => onTabChange("community")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                activeTab === "community"
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              }`}
            >
              <Globe className="w-3.5 h-3.5" />
              <span>Community</span>
            </button>
          </nav>
        )}

        {/* Actions */}
        <div className="flex items-center gap-3">
          {user ? (
            <>
              <button
                onClick={onOpenGoalModal}
                className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-purple-600 text-white text-xs font-semibold shadow-md shadow-indigo-600/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>New Goal</span>
              </button>

              <div className="flex items-center gap-3 pl-3 border-l border-slate-800">
                <div className="flex items-center gap-2 text-sm text-slate-300">
                  <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-bold text-indigo-400">
                    {user.full_name ? user.full_name[0].toUpperCase() : user.email[0].toUpperCase()}
                  </div>
                  <span className="hidden lg:inline font-medium text-xs text-slate-200">
                    {user.full_name || user.email}
                  </span>
                </div>

                <button
                  onClick={onLogout}
                  title="Sign out"
                  className="p-2 text-slate-400 hover:text-rose-400 hover:bg-slate-900 rounded-lg transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            </>
          ) : (
            <button
              onClick={onOpenAuthModal}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-all"
            >
              <User className="w-4 h-4" />
              <span>Sign In</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
