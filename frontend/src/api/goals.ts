import { request } from "./http";
import type { GoalCreateRequest, GoalResponse, RoadmapDetailResponse } from "./types";

export async function createGoalAndRoadmap(
  payload: GoalCreateRequest
): Promise<RoadmapDetailResponse> {
  return request<RoadmapDetailResponse>("POST", "/goals", {
    body: payload,
  });
}

export async function listGoals(): Promise<GoalResponse[]> {
  return request<GoalResponse[]>("GET", "/goals");
}

export async function getGoalById(goalId: string): Promise<GoalResponse> {
  return request<GoalResponse>("GET", `/goals/${goalId}`);
}
