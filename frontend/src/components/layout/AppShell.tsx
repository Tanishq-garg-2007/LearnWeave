import React, { useState, useRef, useEffect } from "react";
import { NavLink, Link, Outlet, useLocation } from "react-router-dom";
import { cn } from "@/lib/cn";
import { Button } from "@/components/ui/Button";
import { Avatar } from "@/components/ui/Avatar";
import { AppBackground } from "./AppBackground";
import { useAuth } from "@/features/auth/AuthProvider";
import {
  Compass,
  BookOpen,
  Calendar,
  Users,
  Plus,
  Sparkles,
  User,
  Target,
  LogOut,
  ChevronDown,
  LayoutDashboard,
  History,
} from "lucide-react";

interface NavItem {
  label: string;
  to: string;
  icon: React.ComponentType<{ className?: string }>;
  authOnly?: boolean;
}

const navItems: NavItem[] = [
  { label: "Dashboard", to: "/dashboard", icon: LayoutDashboard, authOnly: true },
  { label: "Roadmap", to: "/roadmap", icon: Compass },
  { label: "Notes", to: "/notes", icon: BookOpen },
  { label: "Schedule", to: "/schedule", icon: Calendar },
  { label: "Community", to: "/community", icon: Users },
];

export interface AppShellProps {
  children?: React.ReactNode;
}

export function AppShell({ children }: AppShellProps): JSX.Element {
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const location = useLocation();
  const { user, status, logout } = useAuth();

  const isAuthenticated = status === "authenticated";

  useEffect(() => {
    setUserMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSignOut = () => {
    logout();
  };

  const visibleNavItems = navItems.filter((item) => !item.authOnly || isAuthenticated);

  return (
    <div className="min-h-screen bg-[#E8DFD3] text-text p-1.5 sm:p-4 lg:p-6 flex flex-col justify-between selection:bg-cyan/30 selection:text-ink">
      {/* Outer Application Canvas matching reference */}
      <div className="w-full max-w-[1440px] mx-auto min-h-[calc(100vh-2rem)] rounded-[24px] sm:rounded-[36px] border border-white/90 shadow-[0_28px_85px_-15px_rgba(40,30,55,0.12)] overflow-hidden relative flex flex-col bg-white/20">
        <AppBackground variant="wave" />

        {/* Skip to content accessible bypass link */}
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2.5 focus:bg-ink focus:text-white focus:rounded-full focus:shadow-glass focus:outline-none focus:ring-2 focus:ring-focus font-medium text-xs tracking-wide"
        >
          Skip to content
        </a>

        {/* Top Header */}
        <header className="sticky top-0 z-40 w-full bg-white/45 backdrop-blur-2xl border-b border-white/60">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
            {/* Brand Logo */}
            <Link
              to={isAuthenticated ? "/dashboard" : "/"}
              className="flex items-center gap-2.5 group rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            >
              <div className="h-9 w-9 rounded-2xl bg-[#252229] flex items-center justify-center text-white shadow-soft group-hover:scale-105 transition-transform">
                <Sparkles className="w-4 h-4 text-cyan-300" />
              </div>
              <div className="flex items-baseline gap-1.5">
                <span className="font-display text-2xl font-bold tracking-tight text-ink">
                  LearnWeave
                </span>
                <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded-md bg-cyan-100 text-cyan-800 border border-cyan-200">
                  AI
                </span>
              </div>
            </Link>

            {/* Desktop Navigation Links */}
            <nav
              aria-label="Primary navigation"
              className="hidden md:flex items-center gap-1.5 p-1 rounded-full bg-white/50 border border-white/70 shadow-sm backdrop-blur-xl"
            >
              {visibleNavItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    cn(
                      "px-4 py-2 rounded-full text-xs font-semibold tracking-wide transition-all select-none",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-1",
                      isActive
                        ? "bg-[#252229] text-white shadow-sm"
                        : "text-muted hover:text-text hover:bg-black/5"
                    )
                  }
                >
                  {({ isActive }) => (
                    <span aria-current={isActive ? "page" : undefined}>{item.label}</span>
                  )}
                </NavLink>
              ))}
            </nav>

            {/* Header Action Controls */}
            <div className="flex items-center gap-3">
              {isAuthenticated ? (
                <>
                  <Link to="/onboarding" className="hidden sm:inline-flex">
                    <button
                      type="button"
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#252229] hover:bg-[#1a171d] text-white text-xs font-semibold shadow-md transition-all active:scale-95"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>New Goal</span>
                    </button>
                  </Link>

                  {/* Avatar menu */}
                  <div className="relative" ref={userMenuRef}>
                    <button
                      type="button"
                      aria-expanded={userMenuOpen}
                      aria-haspopup="true"
                      aria-label="User profile menu"
                      onClick={() => setUserMenuOpen(!userMenuOpen)}
                      className="flex items-center gap-1.5 p-1 rounded-full hover:bg-black/5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                    >
                      <Avatar size="sm" name={user?.full_name || user?.email || "Student"} />
                      <ChevronDown className="w-3.5 h-3.5 text-muted hidden sm:block" />
                    </button>

                    {userMenuOpen && (
                      <div
                        role="menu"
                        aria-orientation="vertical"
                        className="absolute right-0 mt-2 w-52 rounded-2xl bg-white/95 border border-white/80 shadow-glass backdrop-blur-xl p-1.5 z-50 text-xs font-medium space-y-0.5 animate-in fade-in zoom-in-95 duration-150"
                      >
                        <div className="px-3 py-2 border-b border-surface-border mb-1">
                          <p className="font-semibold text-ink truncate">
                            {user?.full_name || "Learner"}
                          </p>
                          <p className="text-[11px] text-muted truncate">{user?.email}</p>
                        </div>

                        <Link
                          to="/dashboard"
                          role="menuitem"
                          className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-text hover:bg-black/5 transition-colors"
                        >
                          <LayoutDashboard className="w-4 h-4 text-muted" />
                          <span>Dashboard</span>
                        </Link>
                        <Link
                          to="/goals"
                          role="menuitem"
                          className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-text hover:bg-black/5 transition-colors"
                        >
                          <Target className="w-4 h-4 text-muted" />
                          <span>My Goals</span>
                        </Link>
                        <Link
                          to="/profile"
                          role="menuitem"
                          className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-text hover:bg-black/5 transition-colors"
                        >
                          <User className="w-4 h-4 text-muted" />
                          <span>Profile & Mastery</span>
                        </Link>
                        <div className="h-px bg-surface-border my-1" />
                        <button
                          type="button"
                          role="menuitem"
                          onClick={handleSignOut}
                          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-danger hover:bg-danger/10 transition-colors"
                        >
                          <LogOut className="w-4 h-4" />
                          <span>Sign out</span>
                        </button>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="flex items-center gap-2.5">
                  <Link to="/login">
                    <button
                      type="button"
                      className="px-4 py-2 rounded-full bg-white/70 hover:bg-white text-ink border border-white/80 text-xs font-semibold transition-all shadow-sm"
                    >
                      Sign In
                    </button>
                  </Link>
                  <Link to="/register">
                    <button
                      type="button"
                      className="px-4 py-2 rounded-full bg-[#252229] hover:bg-[#1a171d] text-white text-xs font-semibold shadow-md transition-all active:scale-95"
                    >
                      Launch App
                    </button>
                  </Link>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main id="main" tabIndex={-1} className="flex-1 pb-24 md:pb-14 focus:outline-none relative z-10">
          {children || <Outlet />}
        </main>

        {/* Clean Interior Canvas Footer */}
        <footer className="w-full border-t border-white/60 py-5 px-6 text-xs text-muted/80 backdrop-blur-sm relative z-10">
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
            <p>© {new Date().getFullYear()} LearnWeave AI — Agentic Collaborative Learning Companion.</p>
            <div className="flex items-center gap-4 text-xs font-medium">
              <Link to="/community" className="hover:text-text transition-colors">
                Community Notes
              </Link>
              <Link to="/roadmap" className="hover:text-text transition-colors">
                Roadmap
              </Link>
              <Link to="/schedule" className="hover:text-text transition-colors">
                Schedule
              </Link>
            </div>
          </div>
        </footer>

        {/* Mobile Bottom Navigation Bar */}
        <nav
          aria-label="Mobile bottom navigation"
          className="md:hidden fixed bottom-2 left-4 right-4 z-40 bg-white/90 backdrop-blur-xl border border-white/80 rounded-2xl px-3 py-2 shadow-glass"
        >
          <div className={cn("grid gap-1", visibleNavItems.length === 5 ? "grid-cols-5" : "grid-cols-4")}>
            {visibleNavItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    cn(
                      "flex flex-col items-center justify-center py-1 px-1 rounded-xl text-[10px] font-medium transition-all select-none",
                      isActive ? "text-ink font-semibold" : "text-muted hover:text-text"
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      <div
                        className={cn(
                          "p-1 rounded-lg transition-all",
                          isActive ? "bg-[#252229] text-white" : "text-muted"
                        )}
                      >
                        <Icon className="w-3.5 h-3.5" />
                      </div>
                      <span className="mt-0.5 truncate max-w-full text-[9px]">{item.label}</span>
                    </>
                  )}
                </NavLink>
              );
            })}
          </div>
        </nav>
      </div>
    </div>
  );
}

export default AppShell;
