import type {
  ApiErrorShape,
  Candidate,
  CandidateDetail,
  DashboardStats,
  HealthInfo,
  JobDescription,
  ScreeningResult,
  ScreeningRunResponse,
  UploadResponse,
} from "../types";

const BASE_URL: string = import.meta.env.VITE_API_URL ?? "/api";

export class ApiError extends Error {
  status: number;
  details?: { field: string; issue: string }[];

  constructor(shape: ApiErrorShape) {
    super(shape.message || "Request failed");
    this.status = shape.status ?? 500;
    this.details = shape.details;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, init);
  } catch {
    throw new ApiError({
      message: "Cannot reach the server. Is the backend running?",
      status: 0,
    });
  }

  if (response.status === 204) return undefined as T;

  let body: unknown = null;
  const text = await response.text();
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = null;
    }
  }

  if (!response.ok) {
    const shaped = (body as { error?: ApiErrorShape } | null)?.error;
    throw new ApiError(
      shaped
        ? { ...shaped, status: response.status }
        : {
            message:
              response.status === 422
                ? "The submitted data failed validation."
                : `Server error (HTTP ${response.status}).`,
            status: response.status,
          },
    );
  }
  return body as T;
}

function jsonInit(method: string, payload: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  };
}

export interface ResultsQuery {
  job_id?: number | null;
  min_score?: number | null;
  shortlisted_only?: boolean;
  skill?: string | null;
  q?: string | null;
  sort_by?: "score" | "name" | "date";
  order?: "asc" | "desc";
}

export const api = {
  health: () => request<HealthInfo>("/health"),

  stats: () => request<DashboardStats>("/stats"),

  uploadResumes: async (files: File[]): Promise<UploadResponse> => {
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    return request<UploadResponse>("/candidates/upload", {
      method: "POST",
      body: form,
    });
  },

  listCandidates: (params: { q?: string; skill?: string } = {}) => {
    const search = new URLSearchParams();
    if (params.q) search.set("q", params.q);
    if (params.skill) search.set("skill", params.skill);
    const qs = search.toString();
    return request<Candidate[]>(`/candidates${qs ? `?${qs}` : ""}`);
  },

  getCandidate: (id: number) => request<CandidateDetail>(`/candidates/${id}`),

  deleteCandidate: (id: number) =>
    request<void>(`/candidates/${id}`, { method: "DELETE" }),

  listJobs: () => request<JobDescription[]>("/jobs"),

  getJob: (id: number) => request<JobDescription>(`/jobs/${id}`),

  createJob: (payload: { title: string; description_text: string }) =>
    request<JobDescription>("/jobs", jsonInit("POST", payload)),

  updateJob: (
    id: number,
    payload: Partial<{ title: string; description_text: string }>,
  ) => request<JobDescription>(`/jobs/${id}`, jsonInit("PATCH", payload)),

  deleteJob: (id: number) =>
    request<void>(`/jobs/${id}`, { method: "DELETE" }),

  runScreening: (payload: {
    job_description_id: number;
    candidate_ids: number[];
    threshold?: number;
  }) => request<ScreeningRunResponse>("/screening/run", jsonInit("POST", payload)),

  listResults: (query: ResultsQuery = {}) => {
    const search = new URLSearchParams();
    if (query.job_id != null) search.set("job_id", String(query.job_id));
    if (query.min_score != null) search.set("min_score", String(query.min_score));
    if (query.shortlisted_only) search.set("shortlisted_only", "true");
    if (query.skill) search.set("skill", query.skill);
    if (query.q) search.set("q", query.q);
    if (query.sort_by) search.set("sort_by", query.sort_by);
    if (query.order) search.set("order", query.order);
    const qs = search.toString();
    return request<ScreeningResult[]>(`/screening/results${qs ? `?${qs}` : ""}`);
  },
};
