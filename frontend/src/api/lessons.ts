import { request, LLM_TIMEOUT_MS } from "./http";
import type {
  LessonGenerateResponse,
  LessonDetailView,
  DoubtResponse,
  AssessmentAttemptItem,
  LessonStructuredContent,
  LessonSection,
} from "./types";

interface RawLessonSection {
  heading?: string;
  title?: string;
  content?: string;
  explanation?: string;
  cited_chunk_ids?: string[];
}

interface RawLessonContent {
  sections?: RawLessonSection[];
  key_takeaways?: string[];
  grounding_type?: string;
  cited_note_ids?: string[];
}

interface RawLessonResponse {
  id: string;
  title: string;
  module_id: string;
  module_title?: string | null;
  status: "pending" | "in_progress" | "completed" | "skipped";
  duration_minutes: number;
  learning_objectives?: string[];
  lesson_content?: RawLessonContent | null;
  content?: RawLessonContent | null;
  grounding_type?: string;
}

export function normalizeLessonContent(raw: RawLessonContent | null | undefined): LessonStructuredContent | null {
  if (!raw || !Array.isArray(raw.sections)) return null;
  const sections: LessonSection[] = raw.sections.map((sec) => ({
    title: sec.heading ?? sec.title ?? "",
    explanation: sec.content ?? sec.explanation ?? "",
    cited_chunk_ids: sec.cited_chunk_ids ?? [],
  }));
  return {
    sections,
    key_takeaways: raw.key_takeaways ?? [],
    grounding_type: raw.grounding_type ?? "ai_generated",
    cited_note_ids: raw.cited_note_ids ?? [],
  };
}

export async function generateLesson(lessonId: string): Promise<LessonGenerateResponse> {
  const res = await request<RawLessonResponse>("POST", `/lessons/${lessonId}/generate`, {
    timeoutMs: LLM_TIMEOUT_MS,
  });
  return {
    lesson_id: res.id || lessonId,
    title: res.title,
    status: res.status,
    grounding_type: res.grounding_type || "ai_generated",
    content: normalizeLessonContent(res.content || res.lesson_content),
  };
}

export async function getLesson(lessonId: string): Promise<LessonDetailView> {
  const res = await request<RawLessonResponse>("GET", `/lessons/${lessonId}`);
  return {
    id: res.id,
    title: res.title,
    module_id: res.module_id,
    module_title: res.module_title,
    status: res.status,
    duration_minutes: res.duration_minutes,
    learning_objectives: res.learning_objectives || [],
    content: normalizeLessonContent(res.lesson_content || res.content),
  };
}

export async function askDoubt(lessonId: string, doubt: string): Promise<DoubtResponse> {
  return request<DoubtResponse>("POST", `/lessons/${lessonId}/doubt`, {
    body: { doubt },
    timeoutMs: LLM_TIMEOUT_MS,
  });
}

export async function listLessonAttempts(lessonId: string): Promise<AssessmentAttemptItem[]> {
  return request<AssessmentAttemptItem[]>("GET", `/lessons/${lessonId}/attempts`);
}
