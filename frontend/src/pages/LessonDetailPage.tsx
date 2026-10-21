import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "@/api";
import type { LessonResponse } from "@/api/types";
import { LearningCycleModal } from "@/features/lesson/LearningCycleModal";
import { ArrowLeft, Play, Clock, Sparkles, BookOpen, RotateCw, FileText } from "lucide-react";

export default function LessonDetailPage(): JSX.Element {
  const { lessonId } = useParams<{ lessonId: string }>();
  const [lesson, setLesson] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCycleOpen, setIsCycleOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!lessonId) return;
    setIsLoading(true);
    api
      .getLesson(lessonId)
      .then((data) => setLesson(data))
      .catch(() => {
        // Try generating if not found
        return api.generateLesson(lessonId).then((gen) => setLesson(gen));
      })
      .catch((err) => setError(err?.message || "Failed to load lesson."))
      .finally(() => setIsLoading(false));
  }, [lessonId]);

  if (isLoading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center space-y-3">
        <RotateCw className="w-8 h-8 text-muted animate-spin" />
        <p className="text-xs font-semibold text-muted">Loading educational lesson content...</p>
      </div>
    );
  }

  if (error || !lesson) {
    return (
      <div className="py-16 text-center space-y-4">
        <p className="text-sm text-danger font-semibold">{error || "Lesson not found."}</p>
        <Link to="/roadmap" className="text-xs text-cyan-800 underline font-semibold">
          Return to Roadmap
        </Link>
      </div>
    );
  }

  const lessonObject: LessonResponse = {
    id: lesson.id || lesson.lesson_id,
    module_id: lesson.module_id || "",
    title: lesson.title || "Lesson",
    status: lesson.status || "in_progress",
    duration_minutes: lesson.duration_minutes || 30,
    learning_objectives: lesson.learning_objectives || [],
    order_index: lesson.order_index ?? 0,
  };

  return (
    <div className="py-6 sm:py-10 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto space-y-6 text-left animate-in fade-in duration-200">
      <Link
        to="/roadmap"
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted hover:text-ink transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Back to Roadmap</span>
      </Link>

      <div className="rounded-3xl p-6 sm:p-8 bg-white/55 border border-white/85 shadow-[0_16px_40px_-10px_rgba(40,30,60,0.08)] ring-1 ring-inset ring-white/80 backdrop-blur-2xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-cyan-100/90 text-cyan-800 border border-cyan-200/80 shadow-xs">
              Structured Lesson
            </span>
            <h1 className="text-2xl font-bold text-ink">{lesson.title}</h1>
          </div>

          <button
            type="button"
            onClick={() => setIsCycleOpen(true)}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-[#252229] hover:bg-[#151318] text-white text-xs font-semibold shadow-md active:scale-95 transition-all"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Launch Interactive Learning Cycle</span>
          </button>
        </div>

        <div className="flex items-center gap-3 text-xs text-muted pt-2 border-t border-surface-border/60 font-medium">
          <span className="flex items-center gap-1">
            <Clock className="w-3.5 h-3.5" />
            {lesson.duration_minutes || 30} minutes
          </span>
          <span>•</span>
          <span className="capitalize">{lesson.status || "pending"}</span>
        </div>
      </div>

      {/* Lesson Content Sections */}
      <div className="space-y-4">
        {(lesson.content?.sections || lesson.lesson_content?.sections)?.map((sec: any, idx: number) => (
          <div
            key={idx}
            className="p-6 rounded-3xl bg-white/60 hover:bg-white/85 border border-white/85 shadow-[0_16px_40px_-10px_rgba(40,30,60,0.06)] ring-1 ring-inset ring-white/80 backdrop-blur-xl space-y-2 text-left transition-all"
          >
            <h3 className="text-sm font-bold text-ink flex items-center gap-2">
              <span className="w-5 h-5 rounded-md bg-black/5 text-[10px] flex items-center justify-center font-mono">
                {idx + 1}
              </span>
              {sec.title || sec.heading || `Section ${idx + 1}`}
            </h3>
            <p className="text-xs text-text/80 leading-relaxed whitespace-pre-line pl-7">
              {sec.explanation || sec.content}
            </p>
          </div>
        ))}
      </div>

      <LearningCycleModal
        lesson={lessonObject}
        isOpen={isCycleOpen}
        onClose={() => setIsCycleOpen(false)}
      />
    </div>
  );
}
