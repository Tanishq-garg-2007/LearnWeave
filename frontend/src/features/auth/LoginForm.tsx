import React, { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthProvider";
import { GlassCard } from "@/components/ui/GlassCard";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label, FieldHint, FieldError } from "@/components/ui/FormField";
import { Eye, EyeOff, Sparkles, BookOpen, ArrowRight } from "lucide-react";

export function LoginForm(): JSX.Element {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

  // Return to intended page or dashboard
  const destination = (location.state as { from?: Location })?.from?.pathname || "/dashboard";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setServerError(null);
    setEmailError(null);
    setPasswordError(null);

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setEmailError("Please enter your email address.");
      return;
    }
    if (!password) {
      setPasswordError("Please enter your password.");
      return;
    }

    setIsPending(true);
    try {
      await login({ email: trimmedEmail, password });
      navigate(destination, { replace: true });
    } catch (err: unknown) {
      const errorObj = err as Error & { status?: number; details?: unknown };
      const message = errorObj?.message || "Invalid email or password. Please try again.";
      setServerError(message);
      if (message.toLowerCase().includes("email")) {
        setEmailError(message);
      } else if (message.toLowerCase().includes("password")) {
        setPasswordError(message);
      }
    } finally {
      setIsPending(false);
    }
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center py-10 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
        {/* Left Form Panel */}
        <GlassCard padding="lg" className="w-full">
          <div className="mb-6">
            <h1 className="text-3xl font-display font-bold text-text tracking-tight">Welcome Back</h1>
            <p className="text-sm text-muted mt-1 leading-relaxed">
              Sign in to continue your adaptive study sprint.
            </p>
          </div>

          {serverError && (
            <div
              role="alert"
              className="mb-5 p-3.5 rounded-2xl bg-danger/10 border border-danger/20 text-xs font-medium text-danger flex items-start gap-2"
            >
              <span>{serverError}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate className="space-y-5">
            <div>
              <Label htmlFor="login-email" required>
                Email Address
              </Label>
              <Input
                id="login-email"
                type="email"
                autoComplete="email"
                autoFocus
                placeholder="you@example.com"
                value={email}
                disabled={isPending}
                error={Boolean(emailError)}
                aria-describedby={emailError ? "login-email-error" : undefined}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (emailError) setEmailError(null);
                  if (serverError) setServerError(null);
                }}
              />
              <FieldError id="login-email-error">{emailError}</FieldError>
            </div>

            <div>
              <Label htmlFor="login-password" required>
                Password
              </Label>
              <Input
                id="login-password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                placeholder="••••••••"
                value={password}
                disabled={isPending}
                error={Boolean(passwordError)}
                aria-describedby={passwordError ? "login-password-error" : undefined}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (passwordError) setPasswordError(null);
                  if (serverError) setServerError(null);
                }}
                rightIcon={
                  <button
                    type="button"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    onClick={() => setShowPassword(!showPassword)}
                    className="p-1 text-muted hover:text-text transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus rounded-lg"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                }
              />
              <FieldError id="login-password-error">{passwordError}</FieldError>
            </div>

            <Button
              type="submit"
              variant="primary"
              fullWidth
              loading={isPending}
              disabled={isPending}
              rightIcon={<ArrowRight className="w-4 h-4" />}
            >
              Sign In
            </Button>
          </form>

          <div className="mt-6 pt-5 border-t border-surface-border text-center text-xs text-muted">
            Do not have an account?{" "}
            <Link
              to="/register"
              className="font-semibold text-ink hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus rounded"
            >
              Create Account
            </Link>
          </div>
        </GlassCard>

        {/* Right Decorative Graphic Panel */}
        <div className="hidden md:flex flex-col items-center justify-center p-8 rounded-3xl bg-gradient-to-tr from-sky/30 via-lavender/30 to-blush/40 border border-white/60 shadow-glass text-center space-y-6">
          <div className="h-20 w-20 rounded-3xl bg-white/80 shadow-soft flex items-center justify-center text-ink">
            <Sparkles className="w-10 h-10 text-violet" />
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-display font-semibold text-ink">Your Learning Companion</h2>
            <p className="text-xs text-muted max-w-xs leading-relaxed">
              Personalized lessons, adaptive quizzes, and revision schedules tailored to your pace.
            </p>
          </div>

          <div className="w-full max-w-xs p-4 rounded-2xl bg-white/70 border border-white/80 shadow-sm text-left flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-sky/40 flex items-center justify-center text-blue-900 shrink-0">
              <BookOpen className="w-5 h-5" />
            </div>
            <div className="text-xs">
              <p className="font-semibold text-text">Notes-Grounded Learning</p>
              <p className="text-muted">Turn your notes into active sprints</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LoginForm;
