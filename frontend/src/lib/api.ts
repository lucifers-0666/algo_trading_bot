export type ApiHealth = {
  status: "ok" | "degraded";
  mode: "paper";
  service: string;
  timestamp: string;
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

export async function getApiHealth(signal?: AbortSignal): Promise<ApiHealth> {
  const response = await fetch(`${API_BASE}/v1/health`, {
    method: "GET",
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    throw new Error(`Backend returned HTTP ${response.status}`);
  }

  const payload: unknown = await response.json();
  if (
    typeof payload !== "object" ||
    payload === null ||
    !("mode" in payload) ||
    payload.mode !== "paper" ||
    !("timestamp" in payload) ||
    typeof payload.timestamp !== "string"
  ) {
    throw new Error("Backend health response did not match the expected paper-only contract");
  }

  return payload as ApiHealth;
}
