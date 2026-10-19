export class ApiError extends Error {
  status: number;
  details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

export const TOKEN_STORAGE_KEY = "learnweave_token";
export const SESSION_EXPIRED_EVENT = "session-expired";
const DEFAULT_TIMEOUT_MS = 30_000;
export const LLM_TIMEOUT_MS = 150_000;

export type UnauthorizedHandler = () => void;
let unauthorizedHandler: UnauthorizedHandler | null = null;

export function registerUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  unauthorizedHandler = handler;
}

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return sessionStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch {
    // Ignore storage quota or access errors in restricted sandbox
  }
}

export function clearAuthToken(): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // Ignore storage access errors
  }
}

interface ValidationErrorItem {
  loc?: (string | number)[];
  msg?: string;
  type?: string;
}

export function formatApiDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item: unknown) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const valItem = item as ValidationErrorItem;
          const field = Array.isArray(valItem.loc)
            ? valItem.loc.filter((locPart) => locPart !== "body" && locPart !== "query").join(".")
            : "";
          const msg = valItem.msg || "invalid value";
          return field ? `${field}: ${msg}` : msg;
        }
        return "";
      })
      .filter(Boolean);
    if (parts.length > 0) return parts.join("; ");
  }
  return fallback;
}

export interface RequestOptions {
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined | null>;
  signal?: AbortSignal;
  auth?: boolean;
  timeoutMs?: number;
  headers?: Record<string, string>;
}

export async function rawRequest(
  method: string,
  path: string,
  options: RequestOptions = {}
): Promise<Response> {
  const {
    body,
    query,
    signal,
    auth = true,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    headers = {},
  } = options;

  let url = path.startsWith("/") ? `/api/v1${path}` : `/api/v1/${path}`;

  if (query) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null) {
        params.append(key, String(value));
      }
    }
    const queryString = params.toString();
    if (queryString) {
      url += (url.includes("?") ? "&" : "?") + queryString;
    }
  }

  const reqHeaders: Record<string, string> = { ...headers };
  const token = getAuthToken();

  if (token && auth) {
    reqHeaders["Authorization"] = `Bearer ${token}`;
  }

  let requestBody: BodyInit | undefined;
  if (body !== undefined) {
    if (body instanceof FormData || body instanceof Blob) {
      requestBody = body;
    } else {
      if (!reqHeaders["Content-Type"]) {
        reqHeaders["Content-Type"] = "application/json";
      }
      requestBody = JSON.stringify(body);
    }
  }

  const timeoutController = new AbortController();
  const timer = setTimeout(() => timeoutController.abort(), timeoutMs);

  const effectiveSignal = signal
    ? composeAbortSignals(signal, timeoutController.signal)
    : timeoutController.signal;

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers: reqHeaders,
      body: requestBody,
      signal: effectiveSignal,
    });
  } catch (err: unknown) {
    const errorObj = err as Error;
    if (errorObj?.name === "AbortError") {
      throw new ApiError("The request timed out. Please try again.", 0);
    }
    throw new ApiError("Network error. Check your connection and try again.", 0);
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) {
    let errorData: { detail?: unknown } = {};
    try {
      errorData = await response.json();
    } catch {
      errorData = { detail: response.statusText };
    }

    const message = formatApiDetail(
      errorData?.detail,
      `Request failed with status ${response.status}`
    );

    // Handle 401 on authenticated endpoints (excluding login/register)
    if (
      response.status === 401 &&
      token &&
      auth &&
      !path.startsWith("/auth/login") &&
      !path.startsWith("/auth/register")
    ) {
      clearAuthToken();
      if (unauthorizedHandler) {
        unauthorizedHandler();
      }
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
      }
    }

    throw new ApiError(message, response.status, errorData?.detail);
  }

  return response;
}

export async function request<T>(
  method: string,
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const response = await rawRequest(method, path, options);
  if (response.status === 204) {
    return undefined as unknown as T;
  }
  return response.json() as Promise<T>;
}

function composeAbortSignals(sig1: AbortSignal, sig2: AbortSignal): AbortSignal {
  const controller = new AbortController();
  const onAbort = () => controller.abort();
  if (sig1.aborted || sig2.aborted) {
    controller.abort();
    return controller.signal;
  }
  sig1.addEventListener("abort", onAbort);
  sig2.addEventListener("abort", onAbort);
  return controller.signal;
}
