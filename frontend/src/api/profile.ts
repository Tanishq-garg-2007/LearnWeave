import { request, clearAuthToken } from "./http";
import type { LearnerProfileResponse, UpdatePreferencesRequest } from "./types";

export async function updateProfile(
  prefs: UpdatePreferencesRequest
): Promise<LearnerProfileResponse> {
  return request<LearnerProfileResponse>("PUT", "/auth/profile", {
    body: prefs,
  });
}

export async function deleteAccount(): Promise<{ status: string; message: string }> {
  const res = await request<{ status: string; message: string }>("DELETE", "/auth/account");
  clearAuthToken();
  return res;
}
