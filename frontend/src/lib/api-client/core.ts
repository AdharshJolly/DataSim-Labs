export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

interface ParsedApiError {
  message: string;
  code?: string;
  detail?: unknown;
}

export class ApiError extends Error {
  status: number;
  code?: string;
  detail?: unknown;

  constructor(
    message: string,
    options: {
      status: number;
      code?: string;
      detail?: unknown;
    },
  ) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.code = options.code;
    this.detail = options.detail;
  }
}

/**
 * Backward-compatible auth token setter (cookies are authoritative).
 */
export function setAuthToken(token: string, refreshToken?: string): void {
  // Backward compatibility shim during migration to HttpOnly cookies.
  void token;
  void refreshToken;
}

/**
 * Backward-compatible auth token clearer (cookies are authoritative).
 */
export function clearAuthToken(): void {
  // Backward compatibility shim during migration to HttpOnly cookies.
}

async function parseApiErrorDetails(
  response: Response,
): Promise<ParsedApiError> {
  try {
    const payload = (await response.json()) as {
      success?: boolean;
      error?:
        | string
        | {
            code?: string;
            message?: string;
            request_id?: string;
          };
      detail?: string | { message?: string };
      message?: string;
    };

    const code =
      typeof payload.error === "object" && payload.error?.code
        ? payload.error.code
        : undefined;

    if (
      payload.success === false &&
      typeof payload.error === "object" &&
      payload.error?.message
    ) {
      const requestId = payload.error.request_id
        ? ` [request_id=${payload.error.request_id}]`
        : "";
      return {
        message: `${payload.error.message}${requestId}`,
        code,
        detail: payload.detail,
      };
    }
    if (typeof payload.detail === "string") {
      return { message: payload.detail, code, detail: payload.detail };
    }
    if (typeof payload.detail === "object" && payload.detail?.message) {
      return {
        message: payload.detail.message,
        code,
        detail: payload.detail,
      };
    }
    if (typeof payload.message === "string") {
      return { message: payload.message, code, detail: payload.detail };
    }
    if (typeof payload.error === "string") {
      return { message: payload.error, code, detail: payload.detail };
    }
    return {
      message: response.statusText || `HTTP ${response.status}`,
      code,
      detail: payload.detail,
    };
  } catch {
    return {
      message: response.statusText || `HTTP ${response.status}`,
      detail: null,
    };
  }
}

/**
 * Parse an API error response and return a user-friendly message.
 */
export async function parseApiError(response: Response): Promise<string> {
  const parsed = await parseApiErrorDetails(response);
  return parsed.message;
}

export interface TokenRefreshResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

let refreshPromise: Promise<TokenRefreshResponse | null> | null = null;

function shouldRedirectToExpired(detail: string): boolean {
  const normalized = detail.toLowerCase();
  if (normalized.includes("refresh token missing")) return false;
  if (normalized.includes("authentication required")) return false;
  return true;
}

function redirectToExpiredIfNeeded(): void {
  if (typeof window === "undefined") return;
  const path = window.location.pathname;
  if (path.startsWith("/login") || path.startsWith("/register")) return;
  window.location.href = "/login?expired=true";
}

async function attemptRefresh(): Promise<TokenRefreshResponse | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
        credentials: "include",
        cache: "no-store",
      });

      if (!response.ok) {
        const detail = await parseApiError(response);
        if (shouldRedirectToExpired(detail)) {
          redirectToExpiredIfNeeded();
        }
        return null;
      }

      const data = (await response.json()) as TokenRefreshResponse;
      return data;
    } catch {
      redirectToExpiredIfNeeded();
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/**
 * Fetch with auth cookies and retry once after token refresh on 401.
 */
export async function fetchWithAuth(
  url: string | URL,
  init?: RequestInit,
): Promise<Response> {
  const requestInit: RequestInit = {
    ...init,
    credentials: "include",
  };
  let response = await fetch(url, requestInit);

  const urlStr = url.toString();
  if (
    response.status === 401 &&
    !urlStr.includes("/api/v1/auth/refresh") &&
    !urlStr.includes("/api/v1/auth/login") &&
    !urlStr.includes("/api/v1/auth/register")
  ) {
    const newTokens = await attemptRefresh();
    if (newTokens) {
      response = await fetch(url, {
        ...init,
        credentials: "include",
      });
    }
  }

  return response;
}

/**
 * Validate an HTTP response and throw a typed ApiError on failure.
 */
export async function assertResponseOk(response: Response): Promise<void> {
  if (response.ok) {
    return;
  }
  const parsed = await parseApiErrorDetails(response);
  throw new ApiError(`${parsed.message} (${response.status})`, {
    status: response.status,
    code: parsed.code,
    detail: parsed.detail,
  });
}

/**
 * Perform a JSON API request and parse a typed JSON payload.
 */
export async function apiRequest<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetchWithAuth(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    credentials: "include",
    cache: "no-store",
  });

  await assertResponseOk(response);

  return (await response.json()) as T;
}
