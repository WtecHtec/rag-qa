export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

interface ApiErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
    trace_id?: string;
  };
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly traceId?: string,
    readonly code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const hasBody = init?.body !== undefined;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(hasBody ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const payload = await readErrorPayload(response);
    throw new ApiError(
      payload.error?.message ?? `请求失败，状态码 ${response.status}`,
      response.status,
      payload.error?.trace_id ?? response.headers.get("X-Trace-ID") ?? undefined,
      payload.error?.code,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

async function readErrorPayload(response: Response): Promise<ApiErrorEnvelope> {
  try {
    return (await response.json()) as ApiErrorEnvelope;
  } catch {
    // 非 JSON 错误仍由统一 ApiError 表达，调用方不需要理解传输细节。
    return {};
  }
}
