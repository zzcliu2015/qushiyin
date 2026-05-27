export type Platform = "douyin" | "kuaishou";

export type ParseLinkResponse = {
  platform: Platform;
  platformLabel: string;
  normalizedUrl: string;
  title: string | null;
  coverUrl: string | null;
  durationMs: number | null;
  width: number | null;
  height: number | null;
  canFetchDirectly: boolean;
  requiresUpload: boolean;
};

export type JobStatus =
  | "pending"
  | "downloading"
  | "analyzing"
  | "processing"
  | "uploading"
  | "completed"
  | "failed"
  | "expired";

export type JobResponse = {
  jobId: string;
  sourceUrl: string;
  platform: Platform;
  platformLabel: string;
  status: JobStatus;
  progress: number;
  title: string | null;
  outputUrl: string | null;
  errorMessage: string | null;
  createdAt: string;
  updatedAt: string;
};

export type WatermarkRegion = {
  x: number;
  y: number;
  width: number;
  height: number;
};

type CreateJobInput = {
  sourceUrl: string;
  confirmedRights: boolean;
  watermarkMode: "auto";
};

type UploadJobInput = {
  file: File;
  platform: Platform;
  confirmedRights: boolean;
  watermarkRegions?: WatermarkRegion[];
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export function toApiUrl(pathOrUrl: string): string {
  if (/^https?:\/\//.test(pathOrUrl)) {
    return pathOrUrl;
  }

  return `${API_BASE_URL}${pathOrUrl}`;
}

async function requestJson<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      data?.detail ??
      data?.message ??
      `请求失败，HTTP 状态码 ${response.status}`;
    throw new Error(message);
  }

  return data as T;
}

export async function parseLink(url: string): Promise<ParseLinkResponse> {
  return requestJson<ParseLinkResponse>("/api/links/parse", {
    method: "POST",
    body: JSON.stringify({ url })
  });
}

export async function createJob(input: CreateJobInput): Promise<JobResponse> {
  return requestJson<JobResponse>("/api/jobs", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function uploadJob(input: UploadJobInput): Promise<JobResponse> {
  const formData = new FormData();
  formData.append("file", input.file);
  formData.append("platform", input.platform);
  formData.append("confirmed_rights", String(input.confirmedRights));
  if (input.watermarkRegions?.length) {
    formData.append("watermark_regions", JSON.stringify(input.watermarkRegions));
  }

  const response = await fetch(`${API_BASE_URL}/api/jobs/upload`, {
    method: "POST",
    body: formData
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      data?.detail ??
      data?.message ??
      `上传失败，HTTP 状态码 ${response.status}`;
    throw new Error(message);
  }

  return data as JobResponse;
}

export async function getJob(jobId: string): Promise<JobResponse> {
  return requestJson<JobResponse>(`/api/jobs/${jobId}`);
}
