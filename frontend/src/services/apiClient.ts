/**
 * frontend/src/services/apiClient.ts
 * Strongly typed HTTP client communicating with the FastAPI backend.
 * Automatically injects CSRF headers, handles cookie authentication, and provides
 * typed error handling (401 unauthorized, 429 rate limit, 409 conflict).
 */

import type { paths } from "../types/api";

export class ApiError extends Error {
  status: number;
  override message: string;
  detail?: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.message = message;
    this.detail = detail;
  }
}

export class RateLimitError extends ApiError {
  retryAfterSeconds: number;

  constructor(
    retryAfterSeconds: number,
    message: string = `Rate limited. Please retry in ${retryAfterSeconds}s.`
  ) {
    super(429, message);
    this.name = "RateLimitError";
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

export class ConflictError extends ApiError {
  constructor(message: string = "Conflict occurred. State needs to be refreshed.") {
    super(409, message);
    this.name = "ConflictError";
  }
}

/**
 * Extract a cookie by name from document.cookie
 */
export function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp("(^|;\\s*)(" + name + ")=([^;]*)"));
  return match ? decodeURIComponent(match[3]) : null;
}

export interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
}

export async function apiFetch<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  let url = endpoint;
  if (options.params) {
    const searchParams = new URLSearchParams();
    for (const [key, val] of Object.entries(options.params)) {
      if (val !== undefined && val !== null) {
        searchParams.append(key, String(val));
      }
    }
    const query = searchParams.toString();
    if (query) {
      url += (url.includes("?") ? "&" : "?") + query;
    }
  }

  const method = (options.method || "GET").toUpperCase();
  const headers = new Headers(options.headers || {});

  // For JSON payloads
  if (options.body && !(options.body instanceof FormData) && !(options.body instanceof Blob)) {
    if (!headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
  }

  // Inject CSRF Token on mutating calls (POST, PUT, DELETE, PATCH)
  if (["POST", "PUT", "DELETE", "PATCH"].includes(method)) {
    const csrfToken = getCookie("csrf_token");
    if (csrfToken) {
      headers.set("X-CSRF-Token", csrfToken);
    }
  }

  const res = await fetch(url, {
    ...options,
    method,
    headers,
    credentials: "include", // Ensures httpOnly session cookies are transmitted
  });

  if (!res.ok) {
    let errorDetail: any = null;
    let message = `Request failed with status ${res.status}`;

    try {
      const data = await res.json();
      errorDetail = data;
      if (typeof data.detail === "string") {
        message = data.detail;
      } else if (data.detail && typeof data.detail === "object") {
        message = JSON.stringify(data.detail);
      } else if (data.message) {
        message = data.message;
      }
    } catch {
      // response was not JSON
      try {
        message = await res.text();
      } catch {
        // fallback message
      }
    }

    if (res.status === 429) {
      const retryAfterHeader = res.headers.get("Retry-After");
      let retrySeconds = 60;
      if (retryAfterHeader) {
        const parsed = parseInt(retryAfterHeader, 10);
        if (!isNaN(parsed) && parsed > 0) {
          retrySeconds = parsed;
        }
      }
      throw new RateLimitError(retrySeconds, message || `Rate limit reached. Please wait ${retrySeconds}s.`);
    }

    if (res.status === 409) {
      throw new ConflictError(message);
    }

    if (res.status === 401) {
      // Trigger global unauthorized event if not on auth endpoints
      if (!url.startsWith("/api/auth/login") && !url.startsWith("/api/auth/register") && !url.startsWith("/api/auth/guest")) {
        window.dispatchEvent(new CustomEvent("interview_auth_unauthorized"));
      }
    }

    throw new ApiError(res.status, message, errorDetail);
  }

  // Handle empty bodies (e.g. 204 No Content or empty logout)
  if (res.status === 204 || res.headers.get("content-length") === "0") {
    return {} as T;
  }

  try {
    return (await res.json()) as T;
  } catch {
    return {} as T;
  }
}

export interface StartInterviewResponse {
  status: string;
  session_id: number;
  domain: string;
  question: string;
  turn_number: number;
  current_subtopic?: string;
  current_difficulty?: string;
}

// Typed endpoints shortcuts
export const api = {
  // Auth
  register: (body: paths["/api/auth/register"]["post"]["requestBody"]["content"]["application/json"]) =>
    apiFetch<paths["/api/auth/register"]["post"]["responses"]["201"]["content"]["application/json"]>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  login: (body: paths["/api/auth/login"]["post"]["requestBody"]["content"]["application/json"]) =>
    apiFetch<paths["/api/auth/login"]["post"]["responses"]["200"]["content"]["application/json"]>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  guest: () =>
    apiFetch<paths["/api/auth/guest"]["post"]["responses"]["201"]["content"]["application/json"]>("/api/auth/guest", {
      method: "POST",
    }),

  me: () =>
    apiFetch<paths["/api/auth/me"]["get"]["responses"]["200"]["content"]["application/json"]>("/api/auth/me"),

  logout: () =>
    apiFetch<paths["/api/auth/logout"]["post"]["responses"]["200"]["content"]["application/json"]>("/api/auth/logout", {
      method: "POST",
    }),

  // Profile
  getProfile: () =>
    apiFetch<any>("/api/profile"),

  updateProfile: (body: paths["/api/profile"]["put"]["requestBody"]["content"]["application/json"]) =>
    apiFetch<any>("/api/profile", {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  // Domains
  getDomains: () =>
    apiFetch<paths["/api/domains"]["get"]["responses"]["200"]["content"]["application/json"]>("/api/domains"),

  // Interviews
  startInterview: (body: paths["/api/interviews/start"]["post"]["requestBody"]["content"]["application/json"]) =>
    apiFetch<StartInterviewResponse>("/api/interviews/start", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getInterview: (sessionId: string | number) =>
    apiFetch<any>(`/api/interviews/${sessionId}`),

  submitAnswer: (sessionId: string | number, body: paths["/api/interviews/{session_id}/answer"]["post"]["requestBody"]["content"]["application/json"]) =>
    apiFetch<paths["/api/interviews/{session_id}/answer"]["post"]["responses"]["200"]["content"]["application/json"]>(
      `/api/interviews/${sessionId}/answer`,
      {
        method: "POST",
        body: JSON.stringify(body),
      }
    ),

  endInterview: (sessionId: string | number) =>
    apiFetch<paths["/api/interviews/{session_id}/end"]["post"]["responses"]["200"]["content"]["application/json"]>(
      `/api/interviews/${sessionId}/end`,
      {
        method: "POST",
      }
    ),

  getHistory: (params?: { domain?: string; search?: string; page?: number; page_size?: number }) =>
    apiFetch<any>(
      "/api/interviews/history",
      { params }
    ),

  // Analytics
  getAnalyticsSummary: () =>
    apiFetch<any>("/api/analytics/summary"),

  getTrends: () =>
    apiFetch<any>("/api/analytics/trends"),

  getTopics: () =>
    apiFetch<any>("/api/analytics/topics"),

  getClassifications: () =>
    apiFetch<any>("/api/analytics/classifications"),

  getTimeline: () =>
    apiFetch<any>("/api/analytics/timeline"),

  getCohort: () =>
    apiFetch<any>("/api/analytics/cohort"),

  // Settings
  changePassword: (body: paths["/api/settings/password"]["put"]["requestBody"]["content"]["application/json"]) =>
    apiFetch<any>("/api/settings/password", {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  deleteData: (body: paths["/api/settings/data"]["delete"]["requestBody"]["content"]["application/json"]) =>
    apiFetch<any>("/api/settings/data", {
      method: "DELETE",
      body: JSON.stringify(body),
    }),

  // Health
  getHealth: () =>
    apiFetch<paths["/api/health"]["get"]["responses"]["200"]["content"]["application/json"]>("/api/health"),
};
