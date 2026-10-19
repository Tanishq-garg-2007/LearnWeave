import { request } from "./http";
import type { RoadmapDetailResponse, RoadmapVersionItem } from "./types";

export async function getActiveRoadmap(): Promise<RoadmapDetailResponse> {
  return request<RoadmapDetailResponse>("GET", "/roadmaps/active");
}

export async function getRoadmapById(id: string): Promise<RoadmapDetailResponse> {
  return request<RoadmapDetailResponse>("GET", `/roadmaps/${id}`);
}

export async function getRoadmapVersions(id: string): Promise<RoadmapVersionItem[]> {
  return request<RoadmapVersionItem[]>("GET", `/roadmaps/${id}/versions`);
}

export async function updateLessonStatus(
  lessonId: string,
  newStatus: string
): Promise<{ status: string; lesson_id: string; current_status: string }> {
  return request<{ status: string; lesson_id: string; current_status: string }>(
    "PUT",
    `/roadmaps/lessons/${lessonId}/status`,
    {
      body: { new_status: newStatus },
    }
  );
}
