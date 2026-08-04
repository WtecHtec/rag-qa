import { apiRequest } from "./client";

export interface HealthResponse {
  status: "ok";
  service: string;
  environment: string;
  trace_id: string;
}

export function getHealth(signal?: AbortSignal) {
  return apiRequest<HealthResponse>("/health", { signal });
}

