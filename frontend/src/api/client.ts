import type { GenerateAllocationResponse } from "../types/allocation";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function parseError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    return body.detail || "Request failed.";
  } catch {
    return "Request failed.";
  }
}

export async function healthCheck(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return response.json();
}

export async function generateAllocation(formData: FormData): Promise<GenerateAllocationResponse> {
  const response = await fetch(`${API_BASE}/api/generate-allocation`, {
    method: "POST",
    body: formData
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return response.json();
}

export function workbookDownloadUrl(downloadId: string): string {
  return `${API_BASE}/api/download/${downloadId}`;
}

export function previewWorkbookDownloadUrl(downloadId: string): string {
  return `${API_BASE}/api/download-preview/${downloadId}`;
}
