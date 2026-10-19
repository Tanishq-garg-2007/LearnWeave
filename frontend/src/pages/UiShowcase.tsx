import React, { useState } from "react";
import {
  Button,
  IconButton,
  Input,
  Textarea,
  Select,
  Label,
  FieldHint,
  FieldError,
  Slider,
  Badge,
  ProgressBar,
  Tabs,
  Spinner,
  Skeleton,
  Avatar,
  EmptyState,
  GlassCard,
} from "@/components/ui";
import { AppBackground } from "@/components/layout/AppBackground";
import { Sparkles, ArrowRight, Bell, Trash2, Heart, Search, BookOpen } from "lucide-react";

export interface UiShowcaseProps {
  onOpenModal?: () => void;
  onOpenConfirm?: () => void;
  onShowToast?: () => void;
}

export function UiShowcase({
  onOpenModal,
  onOpenConfirm,
  onShowToast,
}: UiShowcaseProps): JSX.Element {
  const [sliderVal, setSliderVal] = useState(45);
  const [activeTab, setActiveTab] = useState("overview");
  const [btnLoading, setBtnLoading] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [inputError, setInputError] = useState(false);

  return (
    <div className="relative min-h-screen py-12 px-4 sm:px-6 lg:px-8">
      <AppBackground variant="wave" />

      <div className="max-w-5xl mx-auto space-y-12">
        <header className="space-y-3">
          <Badge variant="accent">Design System</Badge>
          <h1 className="text-4xl sm:text-5xl font-display text-text font-normal">
            UI Primitive Library
          </h1>
          <p className="text-muted text-base max-w-2xl">
            Live interactive preview of all accessible components, glass surfaces, and tokens.
          </p>
        </header>

        {/* Dialog & Notification Triggers */}
        <section aria-labelledby="triggers-heading">
          <GlassCard padding="md" className="space-y-4">
            <h2 id="triggers-heading" className="text-lg font-semibold text-text">
              Interactive Dialogs & Notifications
            </h2>
            <div className="flex flex-wrap items-center gap-3">
              <Button
                variant="primary"
                onClick={onOpenModal}
                leftIcon={<Sparkles className="w-4 h-4" />}
              >
                Open Modal
              </Button>
              <Button
                variant="secondary"
                onClick={onOpenConfirm}
                leftIcon={<Trash2 className="w-4 h-4 text-danger" />}
              >
                Trigger Confirm Dialog
              </Button>
              <Button
                variant="ghost"
                onClick={onShowToast}
                leftIcon={<Bell className="w-4 h-4" />}
              >
                Trigger Toast
              </Button>
            </div>
          </GlassCard>
        </section>

        {/* Buttons and IconButtons */}
        <section aria-labelledby="buttons-heading">
          <GlassCard padding="md" className="space-y-6">
            <h2 id="buttons-heading" className="text-lg font-semibold text-text">
              Buttons & IconButtons
            </h2>

            <div className="flex flex-wrap items-center gap-3">
              <Button variant="primary">Primary</Button>
              <Button variant="secondary">Secondary</Button>
              <Button variant="ghost">Ghost</Button>
              <Button variant="danger">Danger</Button>
              <Button
                variant="primary"
                loading={btnLoading}
                onClick={() => setBtnLoading(!btnLoading)}
              >
                {btnLoading ? "Loading..." : "Toggle Spinner"}
              </Button>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <Button size="sm" variant="primary">Small</Button>
              <Button size="md" variant="primary">Medium</Button>
              <Button size="lg" variant="primary" rightIcon={<ArrowRight className="w-4 h-4" />}>
                Large with Icon
              </Button>
            </div>

            <div className="flex items-center gap-3">
              <IconButton aria-label="Favorite note" variant="ghost">
                <Heart className="w-4 h-4" />
              </IconButton>
              <IconButton aria-label="Delete item" variant="danger">
                <Trash2 className="w-4 h-4" />
              </IconButton>
              <IconButton aria-label="Search content" variant="secondary">
                <Search className="w-4 h-4" />
              </IconButton>
              <IconButton aria-label="Loading action" variant="primary" loading>
                <Sparkles className="w-4 h-4" />
              </IconButton>
            </div>
          </GlassCard>
        </section>

        {/* Form Controls */}
        <section aria-labelledby="forms-heading">
          <GlassCard padding="md" className="space-y-6">
            <h2 id="forms-heading" className="text-lg font-semibold text-text">
              Form Controls & Validation
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <Label htmlFor="sample-input" required>
                  Email Address
                </Label>
                <Input
                  id="sample-input"
                  type="email"
                  placeholder="student@learnweave.ai"
                  value={inputValue}
                  onChange={(e) => {
                    setInputValue(e.target.value);
                    setInputError(!e.target.value.includes("@") && e.target.value.length > 0);
                  }}
                  error={inputError}
                  aria-describedby={inputError ? "sample-error" : "sample-hint"}
                />
                {!inputError ? (
                  <FieldHint id="sample-hint">We will never share your email address.</FieldHint>
                ) : (
                  <FieldError id="sample-error">Please enter a valid email address.</FieldError>
                )}
              </div>

              <div>
                <Label htmlFor="sample-select">Study Goal</Label>
                <Select
                  id="sample-select"
                  options={[
                    { value: "ml", label: "Machine Learning & AI" },
                    { value: "web", label: "Full Stack Development" },
                    { value: "ds", label: "Data Structures & Algorithms" },
                  ]}
                />
                <FieldHint id="select-hint">Choose your primary learning sprint topic.</FieldHint>
              </div>

              <div className="md:col-span-2">
                <Label htmlFor="sample-textarea">Learning Objectives</Label>
                <Textarea
                  id="sample-textarea"
                  placeholder="What key skills do you want to master in this sprint?"
                />
              </div>

              <div className="md:col-span-2">
                <Slider
                  label="Daily Study Commitment"
                  min={15}
                  max={120}
                  step={15}
                  value={sliderVal}
                  onChange={setSliderVal}
                  formatValue={(v) => `${v} minutes / day`}
                />
              </div>
            </div>
          </GlassCard>
        </section>

        {/* Badges and Progress */}
        <section aria-labelledby="badges-heading">
          <GlassCard padding="md" className="space-y-6">
            <h2 id="badges-heading" className="text-lg font-semibold text-text">
              Badges & Progress
            </h2>

            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="neutral">Neutral</Badge>
              <Badge variant="info">Info (Cyan)</Badge>
              <Badge variant="success">Success (Live Green)</Badge>
              <Badge variant="warning">Warning (Star Amber)</Badge>
              <Badge variant="accent">Accent (Violet)</Badge>
              <Badge variant="danger">Danger</Badge>
            </div>

            <div className="space-y-4 max-w-md">
              <ProgressBar
                value={65}
                label="Module Progress"
                showValue
              />
              <ProgressBar
                value={90}
                label="Sprint Completion"
                showValue
              />
            </div>
          </GlassCard>
        </section>

        {/* Accessible Tabs */}
        <section aria-labelledby="tabs-heading">
          <GlassCard padding="md" className="space-y-6">
            <h2 id="tabs-heading" className="text-lg font-semibold text-text">
              Accessible Tabs (Arrow Keys Navigation)
            </h2>
            <Tabs
              value={activeTab}
              onChange={setActiveTab}
              tabs={[
                { id: "overview", label: "Curriculum Overview" },
                { id: "lessons", label: "Active Lessons", badge: <Badge variant="accent">8</Badge> },
                { id: "evaluations", label: "Evaluations" },
              ]}
            />
            <div
              id={`tabpanel-${activeTab}`}
              role="tabpanel"
              aria-labelledby={`tab-${activeTab}`}
              className="p-4 rounded-2xl bg-white/50 border border-surface-border text-sm text-muted"
            >
              Currently viewing tab: <strong className="text-text font-semibold">{activeTab}</strong>. Press Left/Right arrow keys while focusing on the tabs to switch.
            </div>
          </GlassCard>
        </section>

        {/* Feedback, Avatars and Empty States */}
        <section aria-labelledby="feedback-heading">
          <GlassCard padding="md" className="space-y-6">
            <h2 id="feedback-heading" className="text-lg font-semibold text-text">
              Avatars, Skeletons & Empty States
            </h2>

            <div className="flex items-center gap-4">
              <Avatar size="sm" name="Ada Lovelace" />
              <Avatar size="md" name="Alan Turing" />
              <Avatar size="lg" name="Grace Hopper" />
              <Avatar size="xl" name="Claude Shannon" />
            </div>

            <div className="flex items-center gap-3">
              <Spinner size="sm" />
              <Spinner size="md" />
              <Spinner size="lg" />
              <span className="text-xs text-muted">Accessible SVG spinners</span>
            </div>

            <div className="space-y-2 max-w-sm">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-10 w-full rounded-2xl" />
            </div>

            <EmptyState
              icon={<BookOpen className="w-8 h-8" />}
              title="No Study Notes Uploaded"
              description="Upload your class notes or PDF documents to activate personalized RAG retrieval."
              action={
                <Button variant="primary" size="sm">
                  Upload First Note
                </Button>
              }
            />
          </GlassCard>
        </section>
      </div>
    </div>
  );
}

export default UiShowcase;
