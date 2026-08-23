import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import * as client from "./api/client";
import type { DashboardStats } from "./types";

const emptyStats: DashboardStats = {
  total_resumes: 12,
  candidates_screened: 9,
  average_match_score: 6.4,
  shortlisted_count: 3,
  total_jobs: 2,
  recent_activity: [
    {
      id: 1,
      candidate_id: 5,
      candidate_name: "Aarav Sharma",
      job_title: "Senior Python Developer",
      match_score: 8.5,
      shortlisted: true,
      screened_at: "2026-08-23T10:00:00Z",
    },
  ],
};

function renderApp(route = "/") {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <App />
    </MemoryRouter>,
  );
}

describe("App shell", () => {
  it("renders the main navigation", () => {
    vi.spyOn(client.api, "stats").mockResolvedValue(emptyStats);
    renderApp();
    expect(screen.getAllByText("Dashboard").length).toBeGreaterThan(0);
    expect(screen.getByText("Upload Resumes")).toBeInTheDocument();
    expect(screen.getByText("Job Descriptions")).toBeInTheDocument();
    expect(screen.getByText("Candidates")).toBeInTheDocument();
    expect(screen.getByText("Screening Results")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });
});

describe("Dashboard", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows stat cards and recent activity from the stats API", async () => {
    const spy = vi.spyOn(client.api, "stats").mockResolvedValue(emptyStats);
    renderApp();
    expect(await screen.findByText("Resumes uploaded")).toBeInTheDocument();
    await waitFor(() => expect(spy).toHaveBeenCalled());
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("Aarav Sharma")).toBeInTheDocument();
    expect(screen.getByText("★ Shortlisted")).toBeInTheDocument();
  });

  it("shows an error banner when the backend is unreachable", async () => {
    vi.spyOn(client.api, "stats").mockRejectedValue(
      new client.ApiError({ message: "Cannot reach the server.", status: 0 }),
    );
    renderApp();
    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent(/cannot reach the server/i);
  });
});
