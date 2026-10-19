import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "./AuthProvider";
import { getActiveRoadmap } from "@/api/roadmaps";
import { GlassCard } from "@/components/ui/GlassCard";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label, FieldHint, FieldError } from "@/components/ui/FormField";
import { Eye, EyeOff, Sparkles, Target, ArrowRight } from "lucide-react";

export function RegisterForm(): JSX.Element {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [serverError, setServerError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [confirmPasswordError, setConfirmPasswordError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setServerError(null);
    setEmailError(null);
    setPasswordError(null);
    setConfirmPasswordError(null);

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setEmailError("Please enter your email address.");
      return;
    }
    if (password.length < 6) {
      setPasswordError("Password must be at least 6 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setConfirmPasswordError("Passwords do not match. Please re-enter.");
      return;
    }

    setIsPending(true);
    try {
      await register({
        email: trimmedEmail,
        password,
        full_name: fullName.trim() || undefined,
      });

      // Check whether user already has an active roadmap
      try {
        const activeRoadmap = await getActiveRoadmap();
        if (activeRoadmap?.id) {
          navigate("/dashboard", { replace: true });
          return;
        }
      } catch {
        // No active roadmap -> go to onboarding
      }

      navigate("/onboarding", { replace: true });
    } catch (err: unknown) {
      const errorObj = err as Error & { status?: number; details?: unknown };
      const message = errorObj?.message || "Registration failed. Please check your details and try again.";
      setServerError(message);
      if (message.toLowerCase().includes("email")) {
        setEmailError(message);
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
            <h1 className="text-3xl font-display font-bold text-text tracking-tight">Create Account</h1>
            <p className="text-sm text-muted mt-1 leading-relaxed">
              Start your journey with adaptive, notes-grounded learning.
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

          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <div>
              <Label htmlFor="register-name">Full Name</Label>
              <Input
                id="register-name"
                type="text"
                autoComplete="name"
                placeholder="Ada Lovelace"
                value={fullName}
                disabled={isPending}
                onChange={(e) => setFullName(e.target.value)}
              />
            </div>

            <div>
              <Label htmlFor="register-email" required>
                Email Address
              </Label>
              <Input
                id="register-email"
                type="email"
                autoComplete="email"
                autoFocus
                placeholder="you@example.com"
                value={email}
                disabled={isPending}
                error={Boolean(emailError)}
                aria-describedby={emailError ? "register-email-error" : undefined}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (emailError) setEmailError(null);
                  if (serverError) setServerError(null);
                }}
              />
              <FieldError id="register-email-error">{emailError}</FieldError>
            </div>

            <div>
              <Label htmlFor="register-password" required>
                Password
              </Label>
              <Input
                id="register-password"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                placeholder="••••••••"
                value={password}
                disabled={isPending}
                error={Boolean(passwordError)}
                aria-describedby={passwordError ? "register-password-error" : "register-password-hint"}
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
              <FieldHint id="register-password-hint">Minimum 6 characters.</FieldHint>
              <FieldError id="register-password-error">{passwordError}</FieldError>
            </div>

            <div>
              <Label htmlFor="register-confirm-password" required>
                Confirm Password
              </Label>
              <Input
                id="register-confirm-password"
                type={showConfirmPassword ? "text" : "password"}
                autoComplete="new-password"
                placeholder="••••••••"
                value={confirmPassword}
                disabled={isPending}
                error={Boolean(confirmPasswordError)}
                aria-describedby={confirmPasswordError ? "register-confirm-error" : undefined}
                onChange={(e) => {
                  setConfirmPassword(e.target.value);
                  if (confirmPasswordError) setConfirmPasswordError(null);
                }}
                rightIcon={
                  <button
                    type="button"
                    aria-label={showConfirmPassword ? "Hide confirm password" : "Show confirm password"}
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="p-1 text-muted hover:text-text transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus rounded-lg"
                  >
                    {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                }
              />
              <FieldError id="register-confirm-error">{confirmPasswordError}</FieldError>
            </div>

            <Button
              type="submit"
              variant="primary"
              fullWidth
              loading={isPending}
              disabled={isPending}
              rightIcon={<ArrowRight className="w-4 h-4" />}
              className="mt-2"
            >
              Create Account
            </Button>
          </form>

          <div className="mt-6 pt-5 border-t border-surface-border text-center text-xs text-muted">
            Already have an account?{" "}
            <Link
              to="/login"
              className="font-semibold text-ink hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus rounded"
            >
              Sign In
            </Link>
          </div>
        </GlassCard>

        {/* Right Decorative Graphic Panel */}
        <div className="hidden md:flex flex-col items-center justify-center p-8 rounded-3xl bg-gradient-to-tr from-blush/30 via-lavender/30 to-sky/40 border border-white/60 shadow-glass text-center space-y-6">
          <div className="h-20 w-20 rounded-3xl bg-white/80 shadow-soft flex items-center justify-center text-ink">
            <Target className="w-10 h-10 text-blue-600" />
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-display font-semibold text-ink">Structured 2-Week Sprints</h2>
            <p className="text-xs text-muted max-w-xs leading-relaxed">
              Define your subject, target mastery level, and available study hours to generate an active roadmap.
            </p>
          </div>

          <div className="w-full max-w-xs p-4 rounded-2xl bg-white/70 border border-white/80 shadow-sm text-left flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-green-100 flex items-center justify-center text-green-900 shrink-0">
              <Sparkles className="w-5 h-5" />
            </div>
            <div className="text-xs">
              <p className="font-semibold text-text">Adaptive Evaluation</p>
              <p className="text-muted">Dynamic remediation when doubts arise</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default RegisterForm;
