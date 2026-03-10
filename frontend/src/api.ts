import type { GenerateRequest, GenerateResult } from "./types";

const API_BASE = "/api";

export async function generateRoutes(
  req: GenerateRequest,
  onProgress?: (step: string, pct: number) => void
): Promise<GenerateResult> {
  const resp = await fetch(`${API_BASE}/generate-stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || "Request failed");
  }

  const reader = resp.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: GenerateResult | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const msg = JSON.parse(line.slice(6));
        if (msg.type === "progress" && onProgress) {
          onProgress(msg.step, msg.pct);
        } else if (msg.type === "result") {
          result = msg.data;
        } else if (msg.type === "error") {
          throw new Error(msg.message);
        }
      }
    }
  }

  if (!result) throw new Error("No result received");
  return result;
}

export async function exportGpx(
  coordinates: [number, number][],
  name: string
): Promise<void> {
  const resp = await fetch(`${API_BASE}/export-gpx`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ coordinates, name }),
  });
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${name}.gpx`;
  a.click();
  URL.revokeObjectURL(url);
}
