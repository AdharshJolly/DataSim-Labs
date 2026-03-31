export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export function setAuthToken(token: string, refreshToken?: string): void {
  // Backward compatibility shim during migration to HttpOnly cookies.
  void token;
  void refreshToken;
}

export function clearAuthToken(): void {
  // Backward compatibility shim during migration to HttpOnly cookies.
}

export async function parseApiError(response: Response): Promise<string> {
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
    if (
      payload.success === false &&
      typeof payload.error === "object" &&
      payload.error?.message
    ) {
      const requestId = payload.error.request_id
        ? ` [request_id=${payload.error.request_id}]`
        : "";
      return `${payload.error.message}${requestId}`;
    }
    if (typeof payload.detail === "string") return payload.detail;
    if (typeof payload.detail === "object" && payload.detail?.message) {
      return payload.detail.message;
    }
    if (typeof payload.message === "string") return payload.message;
    if (typeof payload.error === "string") return payload.error;
  } catch {
    // Ignore parse failure and fallback to status text below.
  }
  return response.statusText || `HTTP ${response.status}`;
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

  if (!response.ok) {
    const detail = await parseApiError(response);
    throw new Error(`${detail} (${response.status})`);
  }

  return (await response.json()) as T;
}
