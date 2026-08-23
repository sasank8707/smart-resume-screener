import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { notifyError, notifySuccess } from "../components/toaster";
import {
  EmptyState,
  ErrorBanner,
  RecommendationBadge,
  ScoreBar,
  Spinner,
} from "../components/ui";
import type {
  Candidate,
  JobDescription,
  ScreeningResult,
  ScreeningRunResponse,
} from "../types";

export default function ScreeningResults() {
  const [params] = useSearchParams();
  const [jobs, setJobs] = useState<JobDescription[] | null>(null);
  const [candidates, setCandidates] = useState<Candidate[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Run panel state
  const [jobId, setJobId] = useState<number | null>(
    params.get("job") ? Number(params.get("job")) : null,
  );
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [threshold, setThreshold] = useState(7);
  const [running, setRunning] = useState(false);
  const [runResponse, setRunResponse] = useState<ScreeningRunResponse | null>(null);

  // Results browsing state
  const [results, setResults] = useState<ScreeningResult[] | null>(null);
  const [filters, setFilters] = useState({
    min_score: 1,
    shortlisted_only: false,
    skill: "",
    q: "",
    sort_by: "score" as "score" | "name" | "date",
    order: "desc" as "asc" | "desc",
    job_id: "" as string,
  });
  const [expanded, setExpanded] = useState<number | null>(null);

  useEffect(() => {
    Promise.all([api.listJobs(), api.listCandidates()])
      .then(([jobList, candidateList]) => {
        setJobs(jobList);
        setCandidates(candidateList);
        if (jobList.length > 0 && params.get("job") === null) {
          setJobId((current) => current ?? jobList[0].id);
        }
      })
      .catch((err: Error) => setLoadError(err.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadResults = useCallback(() => {
    api
      .listResults({
        job_id: filters.job_id ? Number(filters.job_id) : undefined,
        min_score: filters.min_score > 1 ? filters.min_score : undefined,
        shortlisted_only: filters.shortlisted_only || undefined,
        skill: filters.skill || undefined,
        q: filters.q || undefined,
        sort_by: filters.sort_by,
        order: filters.order,
      })
      .then(setResults)
      .catch((err: Error) => notifyError(err.message));
  }, [filters]);

  useEffect(() => {
    const timer = window.setTimeout(loadResults, filters.q || filters.skill ? 300 : 0);
    return () => window.clearTimeout(timer);
  }, [loadResults, filters.q, filters.skill]);

  async function runScreening() {
    if (jobId == null || selectedIds.length === 0) return;
    setRunning(true);
    try {
      const response = await api.runScreening({
        job_description_id: jobId,
        candidate_ids: selectedIds,
        threshold,
      });
      setRunResponse(response);
      setSelectedIds([]);
      notifySuccess(
        `Screened ${response.results.length} candidate(s); ` +
          `${response.results.filter((r) => r.shortlisted).length} shortlisted at ≥${response.threshold}`,
      );
      loadResults();
    } catch (err) {
      notifyError(err instanceof Error ? err.message : "Screening failed");
    } finally {
      setRunning(false);
    }
  }

  const selectedJob = useMemo(
    () => jobs?.find((j) => j.id === jobId) ?? null,
    [jobs, jobId],
  );

  if (loadError) return <ErrorBanner message={loadError} />;
  if (!jobs || !candidates) return <Spinner />;

  return (
    <div>
      {/* -------- Run panel -------- */}
      <div className="card card-pad" style={{ marginBottom: 20 }}>
        <h2 className="section-title">Run a screening</h2>
        <p className="section-hint">
          Pick a job description and the candidates to evaluate. Each match is
          scored 1–10 with an explanation, then candidates meeting the threshold
          are shortlisted.
        </p>

        {jobs.length === 0 ? (
          <div className="info-banner">
            You need a job description first — create one on the{" "}
            <a href="/jobs" style={{ color: "inherit" }}>
              Job Descriptions
            </a>{" "}
            page.
          </div>
        ) : (
          <div className="two-col">
            <div>
              <label className="field-label" htmlFor="job-select">
                Job description
              </label>
              <select
                id="job-select"
                className="select"
                value={jobId ?? ""}
                onChange={(e) => setJobId(Number(e.target.value))}
                data-testid="job-select"
              >
                {jobs.map((job) => (
                  <option key={job.id} value={job.id}>
                    {job.title}
                  </option>
                ))}
              </select>

              {selectedJob && (
                <div className="justification-box">
                  <strong>Required:</strong>{" "}
                  {selectedJob.requirements?.required_skills?.join(", ") ||
                    "none detected"}
                  <br />
                  <strong>Preferred:</strong>{" "}
                  {selectedJob.requirements?.preferred_skills?.join(", ") ||
                    "none"}
                  <br />
                  <strong>Experience:</strong>{" "}
                  {selectedJob.requirements?.experience_expectations ?? "unspecified"}
                </div>
              )}

              <label className="field-label" htmlFor="threshold">
                Shortlist threshold
              </label>
              <div className="range-row" id="threshold">
                <input
                  type="range"
                  min={1}
                  max={10}
                  step={0.5}
                  value={threshold}
                  aria-label="Shortlist threshold"
                  onChange={(e) => setThreshold(Number(e.target.value))}
                />
                <span className="threshold-value" data-testid="threshold-value">
                  {threshold.toFixed(1)}
                </span>
              </div>
            </div>

            <div>
              <label className="field-label">
                Candidates ({selectedIds.length} selected)
              </label>
              {candidates.length === 0 ? (
                <div className="info-banner" style={{ marginBottom: 0 }}>
                  No candidates yet — upload resumes first.
                </div>
              ) : (
                <>
                  <div className="candidate-picker">
                    {candidates.map((candidate) => (
                      <label className="candidate-pick-row" key={candidate.id}>
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(candidate.id)}
                          onChange={(e) =>
                            setSelectedIds((prev) =>
                              e.target.checked
                                ? [...prev, candidate.id]
                                : prev.filter((id) => id !== candidate.id),
                            )
                          }
                        />
                        <span className="cell-main" style={{ fontSize: 13.2 }}>
                          {candidate.candidate_name ?? "Unknown"}
                        </span>
                        <span className="cell-sub" style={{ marginLeft: "auto", textAlign: "right" }}>
                          {candidate.skills.slice(0, 3).join(", ") ||
                            "no skills detected"}
                        </span>
                      </label>
                    ))}
                  </div>
                  <button
                    className="btn btn-primary"
                    style={{ marginTop: 12 }}
                    disabled={running || selectedIds.length === 0}
                    onClick={runScreening}
                    data-testid="run-screening"
                  >
                    {running
                      ? "Screening…"
                      : `▶ Screen ${selectedIds.length || ""} candidate(s)`}
                  </button>
                </>
              )}
            </div>
          </div>
        )}
      </div>

      {/* -------- Latest run banner -------- */}
      {runResponse && (
        <div className="info-banner">
          Last run: <strong>{runResponse.results.length}</strong> candidate(s)
          screened against <strong>{runResponse.job.title}</strong> · provider:{" "}
          <code className="inline">{runResponse.provider_used}</code> ·
          shortlist threshold {runResponse.threshold}/10
        </div>
      )}

      {/* -------- Results browser -------- */}
      <div className="card">
        <div className="filters-bar">
          <div className="grow">
            <input
              className="input"
              placeholder="Search candidate name or email…"
              value={filters.q}
              onChange={(e) => setFilters({ ...filters, q: e.target.value })}
              aria-label="Search results"
            />
          </div>
          <select
            className="select"
            style={{ width: 190 }}
            value={filters.job_id}
            onChange={(e) => setFilters({ ...filters, job_id: e.target.value })}
            aria-label="Filter by job"
          >
            <option value="">All jobs</option>
            {jobs.map((job) => (
              <option key={job.id} value={job.id}>
                {job.title}
              </option>
            ))}
          </select>
          <input
            className="input"
            style={{ width: 140 }}
            placeholder="Skill…"
            value={filters.skill}
            onChange={(e) => setFilters({ ...filters, skill: e.target.value })}
            aria-label="Filter by skill"
          />
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={filters.shortlisted_only}
              onChange={(e) =>
                setFilters({ ...filters, shortlisted_only: e.target.checked })
              }
            />
            Shortlisted only
          </label>
          <label className="range-row" style={{ width: 190 }}>
            <span className="cell-sub" style={{ whiteSpace: "nowrap" }}>
              Min score
            </span>
            <input
              type="range"
              min={1}
              max={10}
              step={0.5}
              value={filters.min_score}
              onChange={(e) =>
                setFilters({ ...filters, min_score: Number(e.target.value) })
              }
            />
            <span className="threshold-value">{filters.min_score.toFixed(1)}</span>
          </label>
          <select
            className="select"
            style={{ width: 150 }}
            value={`${filters.sort_by}:${filters.order}`}
            onChange={(e) => {
              const [sort_by, order] = e.target.value.split(":");
              setFilters({
                ...filters,
                sort_by: sort_by as typeof filters.sort_by,
                order: order as typeof filters.order,
              });
            }}
            aria-label="Sort results"
          >
            <option value="score:desc">Score ↓</option>
            <option value="score:asc">Score ↑</option>
            <option value="name:asc">Name A→Z</option>
            <option value="name:desc">Name Z→A</option>
            <option value="date:desc">Newest first</option>
            <option value="date:asc">Oldest first</option>
          </select>
        </div>

        {!results ? (
          <Spinner />
        ) : results.length === 0 ? (
          <EmptyState
            icon="★"
            title="No screening results"
            hint="Run a screening above — results are stored and ranked automatically."
          />
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: 44 }}>#</th>
                  <th>Candidate</th>
                  <th style={{ minWidth: 170 }}>Match score</th>
                  <th>Status</th>
                  <th>Key skills</th>
                  <th>Recommendation</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {results.map((result) => (
                  <ResultRow
                    key={result.id}
                    result={result}
                    expanded={expanded === result.id}
                    onToggle={() =>
                      setExpanded(expanded === result.id ? null : result.id)
                    }
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function ResultRow({
  result,
  expanded,
  onToggle,
}: {
  result: ScreeningResult;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <tr className="row-click" onClick={onToggle}>
        <td className="cell-sub">{result.rank ?? "—"}</td>
        <td>
          <span className="cell-main">
            {result.candidate_name ?? `Candidate #${result.candidate_id}`}
          </span>
          <div className="cell-sub">{result.candidate_email ?? ""}</div>
        </td>
        <td>
          <ScoreBar score={result.match_score} />
        </td>
        <td>
          {result.shortlisted ? (
            <span className="badge success">★ Shortlisted</span>
          ) : (
            <span className="badge neutral">Below bar</span>
          )}
        </td>
        <td style={{ maxWidth: 260 }}>
          <div className="tag-list">
            {result.candidate_skills.slice(0, 4).map((skill) => (
              <span key={skill} className="tag">
                {skill}
              </span>
            ))}
            {result.candidate_skills.length > 4 && (
              <span className="tag">+{result.candidate_skills.length - 4}</span>
            )}
          </div>
        </td>
        <td>
          <RecommendationBadge recommendation={result.recommendation} />
        </td>
        <td className="cell-sub">{expanded ? "▲" : "▼"}</td>
      </tr>
      {expanded && (
        <tr className="result-expand">
          <td colSpan={7}>
            <div className="result-expand-inner">
              <div>
                <h4 style={{ margin: "0 0 6px" }}>Why this score</h4>
                <p style={{ marginTop: 0 }}>{result.explanation}</p>
                <p>
                  <strong>Experience alignment:</strong>{" "}
                  {result.experience_alignment || "—"}
                </p>
                <p>
                  <strong>Education alignment:</strong>{" "}
                  {result.education_alignment || "—"}
                </p>
                <p className="cell-sub" style={{ fontSize: 12 }}>
                  Scored by {result.llm_provider}
                  {result.llm_model ? ` (${result.llm_model})` : ""} ·{" "}
                  confidence: {result.confidence ?? "n/a"} ·{" "}
                  {new Date(result.created_at).toLocaleString()}
                </p>
              </div>
              <div>
                <h4 style={{ margin: "0 0 6px" }}>Strengths</h4>
                <ul style={{ marginTop: 0, paddingLeft: 18 }}>
                  {result.strengths.map((strength, i) => (
                    <li key={i}>{strength}</li>
                  ))}
                  {result.strengths.length === 0 && <li>—</li>}
                </ul>
                <h4 style={{ margin: "12px 0 6px" }}>Missing requirements</h4>
                <div className="tag-list">
                  {result.missing_skills.length === 0 && (
                    <span className="badge success">None — all covered</span>
                  )}
                  {result.missing_skills.map((missing) => (
                    <span key={missing} className="tag">
                      ✕ {missing}
                    </span>
                  ))}
                </div>
                <h4 style={{ margin: "12px 0 6px" }}>Experience & education</h4>
                {result.candidate_experience.slice(0, 3).map((entry, i) => (
                  <div key={i} style={{ marginBottom: 8, fontSize: 13.2 }}>
                    <strong>{entry.role ?? "Role"}</strong>{" "}
                    <span className="cell-sub">
                      {entry.organization ?? ""}
                      {entry.duration ? ` · ${entry.duration}` : ""}
                    </span>
                  </div>
                ))}
                {result.candidate_education.slice(0, 2).map((edu, i) => (
                  <div key={`edu-${i}`} style={{ fontSize: 13.2 }}>
                    <strong>{edu.degree ?? "Degree"}</strong>{" "}
                    <span className="cell-sub">{edu.institution ?? ""}</span>
                  </div>
                ))}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
