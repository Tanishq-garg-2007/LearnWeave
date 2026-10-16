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

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  };

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || `Request failed with status ${res.status}`);
  }

  if (res.headers.get("content-type")?.includes("audio/")) {
    return (await res.blob()) as unknown as T;
  }

  return res.json();
}

export interface NoteChunk {
  id: string;
  chunk_index: number;
  content: string;
}

export interface NoteItem {
  id: string;
  title: string;
  file_type: string;
  chunk_count: number;
  is_public: boolean;
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
  listNotes: () => request<NoteItem[]>("/notes"),

  uploadNote: (file: File, isPublic = false) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("is_public", String(isPublic));
    return request<NoteItem>("/notes/upload", {
      method: "POST",
      body: formData,
    });
  },

  getNoteById: (noteId: string) => request<NoteItem>(`/notes/${noteId}`),

  deleteNote: (noteId: string) =>
    request<{ status: string; message: string }>(`/notes/${noteId}`, {
      method: "DELETE",
    }),

  // Lessons & Learning
  generateLesson: (lessonId: string, style = "comprehensive") =>
    request<any>(`/lessons/${lessonId}/generate`, {
      method: "POST",
      body: JSON.stringify({ style }),
    }),

  getLesson: (lessonId: string) => request<any>(`/lessons/${lessonId}`),

  askDoubt: (lessonId: string, doubt: string) =>
    request<any>(`/lessons/${lessonId}/doubts`, {
      method: "POST",
      body: JSON.stringify({ doubt }),
    }),

  generateQuiz: (lessonId: string) =>
    request<any>(`/lessons/${lessonId}/quiz`, {
      method: "POST",
    }),

  submitQuiz: (quizId: string, answers: Array<{ question_id: string; answer_text: string }>) =>
    request<any>(`/lessons/quiz/${quizId}/submit`, {
      method: "POST",
      body: JSON.stringify({ answers }),
    }),

  // Learning Cycle State Machine
  startCycle: (lessonId: string) =>
    request<CycleStateResponse>("/cycle/start", {
      method: "POST",
      body: JSON.stringify({ lesson_id: lessonId }),
    }),

  getCycleState: (cycleId: string) => request<CycleStateResponse>(`/cycle/${cycleId}/state`),

  submitCycleStep: (cycleId: string, stepName: string, payload: any) =>
    request<CycleStateResponse>(`/cycle/${cycleId}/step`, {
      method: "POST",
      body: JSON.stringify({ step_name: stepName, payload }),
    }),

  // Voice Pipeline
  speak: async (text: string, voice = "af_heart"): Promise<Blob> => {
    const token = getAuthToken();
    const res = await fetch(`${API_BASE}/voice/speak`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ text, voice }),
    });
    if (!res.ok) throw new Error("TTS synthesis failed");
    return res.blob();
  },

  listen: async (audioBlob: Blob): Promise<{ transcription: string }> => {
    const token = getAuthToken();
    const formData = new FormData();
    formData.append("file", audioBlob, "audio.wav");
    const res = await fetch(`${API_BASE}/voice/listen`, {
      method: "POST",
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: formData,
    });
    if (!res.ok) throw new Error("STT transcription failed");
    return res.json();
  },

  // Schedules
  getSchedule: (roadmapId: string) => request<ScheduleItem[]>(`/schedule/${roadmapId}`),

  generateSchedule: (roadmapId: string, startDate?: string) =>
    request<ScheduleItem[]>("/schedule/generate", {
      method: "POST",
      body: JSON.stringify({ roadmap_id: roadmapId, start_date: startDate }),
    }),

  completeScheduleSession: (scheduleId: string) =>
    request<ScheduleItem>(`/schedule/${scheduleId}/complete`, {
      method: "PUT",
    }),

  // Community Library
  getCommunityNotes: async (sort: "wilson" | "recent" = "wilson", search?: string): Promise<NoteItem[]> => {
    const params = new URLSearchParams({ sort_by: sort });
    if (search) params.append("query", search);
    const res = await request<any>(`/community/notes?${params.toString()}`);
    return (Array.isArray(res) ? res : res.notes || []) as NoteItem[];
  },

  voteCommunityNote: (noteId: string, voteType: "upvote" | "downvote") =>
    request<{ status: string; new_wilson_score: number; upvotes: number; downvotes: number }>(
      `/community/notes/${noteId}/vote`,
      {
        method: "POST",
        body: JSON.stringify({ vote_type: voteType }),
      }
    ),

  importCommunityNote: (noteId: string) =>
    request<{ status: string; new_note_id: string; title: string; chunks_imported: number }>(
      `/community/notes/${noteId}/import`,
      {
        method: "POST",
      }
    ),

  reportCommunityNote: (noteId: string, reason = "Inappropriate or inaccurate content") =>
    request<{ status: string; report_count: number; is_quarantined: boolean }>(
      `/community/notes/${noteId}/report`,
      {
        method: "POST",
        body: JSON.stringify({ reason }),
      }
    ),

  publishNote: (noteId: string, isPublic: boolean) =>
    request<{ status: string; note_id: string; is_public: boolean }>(
      `/community/notes/${noteId}/publish`,
      {
        method: "PUT",
        body: JSON.stringify({ is_public: isPublic }),
      }
    ),

  // Health
  checkHealth: () => request<{ status: string }>("/health"),
  checkReadiness: () => request<{ status: string; checks: Record<string, boolean> }>("/ready"),
};
