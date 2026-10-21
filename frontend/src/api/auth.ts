import { request, setAuthToken, clearAuthToken } from "./http";
import type {
  UserRegisterRequest,
  UserLoginRequest,
  TokenResponse,
  UserResponse,
  LearnerProfileResponse,
  UpdatePreferencesRequest,
} from "./types";

export async function register(payload: UserRegisterRequest): Promise<TokenResponse> {
  const res = await request<TokenResponse>("POST", "/auth/register", {
    body: payload,
    auth: false,
  });
  if (res.access_token) {
    setAuthToken(res.access_token);
  }
  return res;
}

export async function login(payload: UserLoginRequest): Promise<TokenResponse> {
  const res = await request<TokenResponse>("POST", "/auth/login", {
    body: payload,
    auth: false,
  });
  if (res.access_token) {
    setAuthToken(res.access_token);
  }
  return res;
}

export async function getMe(): Promise<UserResponse> {
  return request<UserResponse>("GET", "/auth/me");
}

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
