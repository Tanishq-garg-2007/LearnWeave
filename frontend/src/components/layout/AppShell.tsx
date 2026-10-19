import React, { useState, useRef, useEffect } from "react";
import { NavLink, Link, Outlet, useLocation } from "react-router-dom";
import { cn } from "@/lib/cn";
import { Button } from "@/components/ui/Button";
import { Avatar } from "@/components/ui/Avatar";
import { AppBackground } from "./AppBackground";
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
} from "lucide-react";

interface NavItem {
  label: string;
  to: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navItems: NavItem[] = [
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

  // Check if token exists in localStorage
  const token = typeof window !== "undefined" ? localStorage.getItem("learnweave_token") : null;
  const isAuthenticated = Boolean(token);

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
    localStorage.removeItem("learnweave_token");
    window.location.href = "/login";
  };

  return (
    <div className="min-h-screen flex flex-col bg-bg text-text relative selection:bg-cyan/30 selection:text-ink">
      <AppBackground />

      {/* Skip to content accessible bypass link */}
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2.5 focus:bg-ink focus:text-white focus:rounded-full focus:shadow-glass focus:outline-none focus:ring-2 focus:ring-focus font-medium text-xs tracking-wide"
      >
        Skip to content
      </a>

      {/* Top Header */}
      <header className="sticky top-0 z-40 w-full bg-white/70 backdrop-blur-xl border-b border-surface-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          {/* Brand Logo */}
          <Link
            to={isAuthenticated ? "/dashboard" : "/"}
            className="flex items-center gap-2.5 group rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          >
            <div className="h-9 w-9 rounded-2xl bg-gradient-to-tr from-accent-from to-accent-to flex items-center justify-center text-white shadow-soft group-hover:scale-105 transition-transform">
              <Sparkles className="w-5 h-5" />
            </div>
            <span className="font-display text-2xl font-bold tracking-tight text-ink">
              LearnWeave
            </span>
          </Link>

          {/* Desktop Navigation Links */}
          <nav
            aria-label="Primary navigation"
            className="hidden md:flex items-center gap-1.5 p-1 rounded-full bg-white/60 border border-surface-border shadow-soft"
          >
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    "px-4 py-2 rounded-full text-xs font-semibold tracking-wide transition-all select-none",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-1",
                    isActive
                      ? "bg-ink text-white shadow-sm"
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
                  <Button
                    variant="primary"
                    size="sm"
                    leftIcon={<Plus className="w-3.5 h-3.5" />}
                  >
                    New goal
                  </Button>
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
                    <Avatar size="sm" name="Learner" />
                    <ChevronDown className="w-3.5 h-3.5 text-muted hidden sm:block" />
                  </button>

                  {userMenuOpen && (
                    <div
                      role="menu"
                      aria-orientation="vertical"
                      className="absolute right-0 mt-2 w-48 rounded-2xl bg-white/95 border border-surface-border shadow-glass backdrop-blur-xl p-1.5 z-50 text-xs font-medium space-y-0.5"
                    >
                      <Link
                        to="/profile"
                        role="menuitem"
                        className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-text hover:bg-black/5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                      >
                        <User className="w-4 h-4 text-muted" />
                        <span>Profile</span>
                      </Link>
                      <Link
                        to="/goals"
                        role="menuitem"
                        className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-text hover:bg-black/5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                      >
                        <Target className="w-4 h-4 text-muted" />
                        <span>Goals</span>
                      </Link>
                      <div className="h-px bg-surface-border my-1" />
                      <button
                        type="button"
                        role="menuitem"
                        onClick={handleSignOut}
                        className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-danger hover:bg-danger/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                      >
                        <LogOut className="w-4 h-4" />
                        <span>Sign out</span>
                      </button>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="flex items-center gap-2">
                <Link to="/login">
                  <Button variant="secondary" size="sm">
                    Sign in
                  </Button>
                </Link>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main id="main" tabIndex={-1} className="flex-1 pb-24 md:pb-12 focus:outline-none">
        {children || <Outlet />}
      </main>

      {/* Small Clean Footer */}
      <footer className="w-full border-t border-surface-border py-6 px-4 text-center text-xs text-muted">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <p>© {new Date().getFullYear()} LearnWeave AI. Adaptive Learning Companion.</p>
          <div className="flex items-center gap-4">
            <Link to="/community" className="hover:text-text transition-colors">
              Community Notes
            </Link>
            <Link to="/roadmap" className="hover:text-text transition-colors">
              Active Roadmap
            </Link>
          </div>
        </div>
      </footer>

      {/* Mobile Fixed Bottom Navigation Bar */}
      <nav
        aria-label="Mobile bottom navigation"
        className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white/85 backdrop-blur-xl border-t border-surface-border px-4 py-2 pb-[env(safe-area-inset-bottom,0.75rem)] shadow-lg"
      >
        <div className="grid grid-cols-4 gap-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    "flex flex-col items-center justify-center py-1.5 px-2 rounded-2xl text-[10px] font-medium transition-all select-none",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
                    isActive
                      ? "text-ink font-semibold"
                      : "text-muted hover:text-text"
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <div
                      className={cn(
                        "p-1 rounded-xl transition-all",
                        isActive ? "bg-ink text-white" : "text-muted"
                      )}
                    >
                      <Icon className="w-4 h-4" />
                    </div>
                    <span
                      className="mt-1"
                      aria-current={isActive ? "page" : undefined}
                    >
                      {item.label}
                    </span>
                  </>
                )}
              </NavLink>
            );
          })}
        </div>
      </nav>
    </div>
  );
}

export default AppShell;
