const API_BASE = "/api/v1";

export interface UserProfile {
  id: string;
  email: string;
  full_name?: string;
  workspace_id?: string;
  profile?: {
    preferences: Record<string, any>;
    topic_mastery: Record<string, number>;
    weak_areas: string[];
    unresolved_doubts: any[];
    completed_lessons: string[];
  };
}

export interface Lesson {
  id: string;
  module_id: string;
  title: string;
  learning_objectives: string[];
  order_index: number;
  status: "pending" | "in_progress" | "completed" | "skipped";
  duration_minutes: number;
  prerequisites: string[];
}

export interface Module {
  id: string;
  roadmap_id: string;
  title: string;
  description?: string;
  order_index: number;
  is_planned_later: boolean;
  target_week: number;
  estimated_hours: number;
  lessons: Lesson[];
}

export interface Roadmap {
  id: string;
  goal_id: string;
  user_id: string;
  title: string;
  version: number;
  is_active: boolean;
  total_modules: number;
  total_lessons: number;
  modules: Module[];
}

export interface CreateGoalPayload {
  subject: string;
  target_level: string;
  current_level: string;
  total_duration_weeks: number;
  hours_per_week: number;
  preferred_style: string;
  specific_objectives: string[];
}

export function getAuthToken(): string | null {
  return localStorage.getItem("learnweave_token");
}

export function setAuthToken(token: string): void {
  localStorage.setItem("learnweave_token", token);
}

export function clearAuthToken(): void {
  localStorage.removeItem("learnweave_token");
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export const UNAUTHORIZED_EVENT = "learnweave:unauthorized";
const DEFAULT_TIMEOUT_MS = 30_000;
export const LLM_TIMEOUT_MS = 150_000;

/** FastAPI errors: `detail` is a string, or an array of {loc, msg} for 422 validation errors. */
export function formatApiDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((d: any) => {
        if (typeof d === "string") return d;
        const field = Array.isArray(d?.loc) ? d.loc.filter((x: any) => x !== "body" && x !== "query").join(".") : "";
        const msg = d?.msg ?? "invalid value";
        return field ? `${field}: ${msg}` : msg;
      })
      .filter(Boolean);
    if (parts.length) return parts.join("; ");
  }
  return fallback;
}

async function rawRequest(endpoint: string, options: RequestInit & { timeoutMs?: number; auth?: boolean } = {}): Promise<Response> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, auth = true, ...init } = options;
  const token = getAuthToken();
  const headers: Record<string, string> = { ...((init.headers as Record<string, string>) || {}) };

  if (init.body && !(init.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  if (token && auth) headers["Authorization"] = `Bearer ${token}`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${endpoint}`, { ...init, headers, signal: controller.signal });
  } catch (err: any) {
    if (err?.name === "AbortError") throw new ApiError("The request timed out. Please try again.", 0);
    throw new ApiError("Network error. Check your connection and try again.", 0);
  } finally {
    clearTimeout(timer);
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    const message = formatApiDetail(errorData?.detail, `Request failed with status ${res.status}`);
    // An expired or invalid token on an authenticated call ends the session (not login/register failures).
    if (res.status === 401 && token && auth && !endpoint.startsWith("/auth/login") && !endpoint.startsWith("/auth/register")) {
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    }
    throw new ApiError(message, res.status);
  }
  return res;
}

async function request<T>(endpoint: string, options: RequestInit & { timeoutMs?: number; auth?: boolean } = {}): Promise<T> {
  const res = await rawRequest(endpoint, options);
  if (res.status === 204) return undefined as unknown as T;
  return res.json();
}

export interface NoteChunk {
  id: string;
  chunk_index: number;
  content: string; // backend: text_content
}

export interface NoteItem {
  id: string;
  title: string;
  file_type: string;
  chunk_count: number;
  is_public: boolean; // derived from backend `visibility`
  visibility?: string;
  subject?: string;
  upvotes: number;
  downvotes: number;
  wilson_score: number;
  created_at: string;
  chunks?: NoteChunk[];
}

export interface CycleStateResponse {
  cycle_id: string;
  lesson_id: string;
  current_step: string;
  completed_steps: string[];
  context: Record<string, any>;
  is_finished: boolean;
}

export interface ScheduleItem {
  id: string;
  lesson_id: string;
  lesson_title?: string;
  scheduled_date: string;
  estimated_minutes: number;
  session_type: "standard_lesson" | "spaced_repetition";
  status: "pending" | "completed" | "skipped";
}


// ---- Backend -> UI normalizers (the backend contract is the source of truth) ----
function normalizeNote(n: any): NoteItem {
  return {
    ...n,
    is_public: n.visibility === "public",
    chunk_count: n.chunk_count ?? n.chunks?.length ?? 0,
    upvotes: n.upvotes ?? 0,
    downvotes: n.downvotes ?? 0,
    wilson_score: n.wilson_score ?? 0,
    chunks: Array.isArray(n.chunks)
      ? n.chunks.map((c: any) => ({ id: c.id, chunk_index: c.chunk_index, content: c.text_content ?? c.content ?? "" }))
      : undefined,
  };
}

function normalizeLessonContent(c: any) {
  if (!c || !Array.isArray(c.sections)) return null;
  return {
    ...c,
    sections: c.sections.map((sec: any) => ({
      title: sec.heading ?? sec.title ?? "",
      explanation: sec.content ?? sec.explanation ?? "",
      cited_chunk_ids: sec.cited_chunk_ids ?? [],
    })),
    key_takeaways: c.key_takeaways ?? [],
  };
}

function normalizeQuiz(q: any) {
  return {
    quiz_id: q.assessment_id,
    lesson_id: q.lesson_id,
    title: q.title,
    questions: (q.questions || []).map((x: any) => ({
      id: String(x.question_index),
      question_index: x.question_index,
      question_type: x.question_type,
      prompt: x.question,
      // backend sends {"A": "...", "B": "..."}; the UI renders an ordered array
      options: x.options ? Object.keys(x.options).sort().map((k) => x.options[k]) : undefined,
      option_keys: x.options ? Object.keys(x.options).sort() : undefined,
      rubric_criteria: x.rubric_criteria,
    })),
  };
}

function normalizeSession(s: any): ScheduleItem {
  return {
    id: s.id,
    lesson_id: s.lesson_id,
    lesson_title: s.lesson_title,
    scheduled_date: s.scheduled_date,
    estimated_minutes: s.duration_minutes ?? 0,
    session_type: s.is_revision ? "spaced_repetition" : "standard_lesson",
    status: s.status === "completed" || s.status === "skipped" ? s.status : "pending",
  };
}

export const api = {
  // Auth
  register: (payload: { email: string; password: string; full_name?: string }) =>
    request<{ access_token: string; user_id: string; email: string; workspace_id: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  login: (payload: { email: string; password: string }) =>
    request<{ access_token: string; user_id: string; email: string; workspace_id: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getMe: () => request<UserProfile>("/auth/me"),

  updateProfile: (prefs: Record<string, any>) =>
    request("/auth/profile", {
      method: "PUT",
      body: JSON.stringify(prefs),
    }),

  // Goals & Roadmaps
  createGoalAndRoadmap: (payload: CreateGoalPayload) =>
    request<Roadmap>("/goals", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getActiveRoadmap: () => request<Roadmap>("/roadmaps/active"),

  getRoadmapById: (id: string) => request<Roadmap>(`/roadmaps/${id}`),

  getRoadmapVersions: (id: string) =>
    request<Array<{ id: string; version_number: number; change_reason: string; created_at: string }>>(
      `/roadmaps/${id}/versions`
    ),

  updateLessonStatus: (lessonId: string, newStatus: string) =>
    request<{ status: string; lesson_id: string; current_status: string }>(`/roadmaps/lessons/${lessonId}/status`, {
      method: "PUT",
      body: JSON.stringify({ new_status: newStatus }),
    }),

  // Notes
  listNotes: async () => (await request<any[]>("/notes")).map(normalizeNote),

  uploadNote: async (file: File, isPublic = false, subject = "General") => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("subject", subject.trim() || "General");
    formData.append("visibility", isPublic ? "public" : "private");
    const res = await request<any>("/notes/upload", { method: "POST", body: formData, timeoutMs: LLM_TIMEOUT_MS });
    return { ...res, chunk_count: res.chunks_created ?? 0 };
  },

  getNoteById: async (noteId: string) => normalizeNote(await request<any>(`/notes/${noteId}`)),

  deleteNote: (noteId: string) =>
    request<{ status: string; message: string }>(`/notes/${noteId}`, {
      method: "DELETE",
    }),

  // Lessons & Learning
  generateLesson: async (lessonId: string) => {
    const res = await request<any>(`/lessons/${lessonId}/generate`, { method: "POST", timeoutMs: LLM_TIMEOUT_MS });
    return { ...res, content: normalizeLessonContent(res.content) };
  },

  getLesson: async (lessonId: string) => {
    const res = await request<any>(`/lessons/${lessonId}`);
    return { ...res, content: normalizeLessonContent(res.lesson_content) };
  },

  askDoubt: (lessonId: string, doubt: string) =>
    request<{ answer: string; [k: string]: any }>(`/lessons/${lessonId}/doubt`, {
      method: "POST",
      body: JSON.stringify({ doubt }),
      timeoutMs: LLM_TIMEOUT_MS,
    }),

  generateQuiz: async (lessonId: string) =>
    normalizeQuiz(await request<any>(`/lessons/${lessonId}/quiz`, { method: "POST", timeoutMs: LLM_TIMEOUT_MS })),

  /** answers use the normalized quiz shape: question_index + a letter (MCQ) or free text (short answer). */
  submitQuiz: async (
    lessonId: string,
    assessmentId: string,
    answers: Array<{ question_index: number; selected_option?: string; written_answer?: string }>
  ) => {
    const res = await request<any>(`/lessons/${lessonId}/quiz/submit`, {
      method: "POST",
      body: JSON.stringify({ assessment_id: assessmentId, answers }),
      timeoutMs: LLM_TIMEOUT_MS,
    });
    return { ...res, score_percentage: Math.round((res.overall_score ?? 0) * 100) };
  },

  // Learning Cycle State Machine
  startCycle: (lessonId: string) =>
    request<CycleStateResponse>("/cycle/start", {
      method: "POST",
      body: JSON.stringify({ lesson_id: lessonId }),
    }),

  getCycleState: (cycleId: string) => request<CycleStateResponse>(`/cycle/${cycleId}`),

  submitCycleStep: (cycleId: string, stepName: string, inputData: any) =>
    request<CycleStateResponse>(`/cycle/${cycleId}/step`, {
      method: "POST",
      body: JSON.stringify({ step_name: stepName, input_data: inputData }),
      timeoutMs: LLM_TIMEOUT_MS,
    }),

  // Voice Pipeline
  speak: async (text: string, voice = "af_heart"): Promise<Blob> => {
    const res = await rawRequest("/voice/speak", {
      method: "POST",
      body: JSON.stringify({ text: text.slice(0, 5000), voice }),
      timeoutMs: LLM_TIMEOUT_MS,
    });
    return res.blob();
  },

  /** Sends the recorder's real container type; the backend returns {text}. */
  listen: async (audioBlob: Blob): Promise<{ transcription: string }> => {
    const type = audioBlob.type || "audio/webm";
    const ext = type.includes("mp4") ? "mp4" : type.includes("ogg") ? "ogg" : type.includes("wav") ? "wav" : "webm";
    const formData = new FormData();
    formData.append("file", audioBlob, `audio.${ext}`);
    const res = await request<{ text: string }>("/voice/listen", { method: "POST", body: formData, timeoutMs: LLM_TIMEOUT_MS });
    return { transcription: res.text ?? "" };
  },

  // Schedules
  getSchedule: async (roadmapId: string): Promise<ScheduleItem[]> => {
    const res = await request<{ sessions: any[] }>(`/schedule?roadmap_id=${encodeURIComponent(roadmapId)}`);
    return (res.sessions || []).map(normalizeSession);
  },

  /** Regenerates, then reloads: the generate endpoint returns a summary, not the sessions. */
  generateSchedule: async (roadmapId: string): Promise<ScheduleItem[]> => {
    await request("/schedule/generate", { method: "POST", body: JSON.stringify({ roadmap_id: roadmapId }) });
    return api.getSchedule(roadmapId);
  },

  completeScheduleSession: async (scheduleId: string): Promise<ScheduleItem> =>
    normalizeSession(
      await request<any>(`/schedule/${scheduleId}/status`, { method: "PUT", body: JSON.stringify({ status: "completed" }) })
    ),

  // Community Library
  getCommunityNotes: async (sort: "wilson" | "latest" | "upvotes" = "wilson", search?: string): Promise<NoteItem[]> => {
    const params = new URLSearchParams({ sort_by: sort });
    if (search) params.append("query", search);
    const res = await request<any>(`/community/notes?${params.toString()}`);
    return (Array.isArray(res) ? res : res.notes || []).map(normalizeNote);
  },

  voteCommunityNote: (noteId: string, voteType: "upvote" | "downvote") =>
    request<{ upvotes: number; downvotes: number; wilson_score: number; new_wilson_score: number }>(
      `/community/notes/${noteId}/vote`,
      { method: "POST", body: JSON.stringify({ vote_value: voteType === "upvote" ? 1 : -1 }) }
    ),

  importCommunityNote: (noteId: string) =>
    request<{ status: string; new_note_id: string; title: string; chunks_imported: number }>(
      `/community/notes/${noteId}/import`,
      { method: "POST", timeoutMs: LLM_TIMEOUT_MS }
    ),

  reportCommunityNote: async (noteId: string, reason = "Inappropriate or inaccurate content") => {
    const res = await request<{ total_reports: number; quarantined: boolean; message: string }>(
      `/community/notes/${noteId}/report`,
      { method: "POST", body: JSON.stringify({ reason }) }
    );
    return { ...res, report_count: res.total_reports, is_quarantined: res.quarantined };
  },

  publishNote: async (noteId: string, isPublic: boolean) => {
    const res = await request<{ id: string; visibility: string }>(`/community/notes/${noteId}/publish`, {
      method: "PUT",
      body: JSON.stringify({ visibility: isPublic ? "public" : "private" }),
    });
    return { ...res, is_public: res.visibility === "public" };
  },

  // Health
  checkHealth: () => request<{ status: string }>("/health", { auth: false }),
  checkReadiness: () => request<{ status: string; checks: Record<string, boolean> }>("/ready"),
};
