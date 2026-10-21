import { request } from "./http";
import type { ScheduleItem } from "./types";

interface RawSessionItem {
  id: string;
  lesson_id: string;
  lesson_title?: string;
  scheduled_date: string;
  duration_minutes?: number;
  is_revision?: boolean;
  status: string;
}

export function normalizeSession(s: RawSessionItem): ScheduleItem {
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

export async function getSchedule(roadmapId: string): Promise<ScheduleItem[]> {
  const res = await request<{ sessions: RawSessionItem[] }>("GET", "/schedule", {
    query: { roadmap_id: roadmapId },
  });
  return (res.sessions || []).map(normalizeSession);
}

export async function generateSchedule(roadmapId: string): Promise<ScheduleItem[]> {
  await request<{ message: string; sessions_created: number }>("POST", "/schedule/generate", {
    body: { roadmap_id: roadmapId },
  });
  return getSchedule(roadmapId);
}

export async function completeScheduleSession(scheduleId: string): Promise<ScheduleItem> {
  const res = await request<RawSessionItem>("PUT", `/schedule/${scheduleId}/status`, {
    body: { status: "completed" },
  });
  return normalizeSession(res);
}
