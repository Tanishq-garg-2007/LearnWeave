import { request } from "./http";
import type { HealthResponse, ReadinessResponse } from "./types";

export async function checkHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("GET", "/health", { auth: false });
}

export async function checkReadiness(): Promise<ReadinessResponse> {
  return request<ReadinessResponse>("GET", "/ready");
}
