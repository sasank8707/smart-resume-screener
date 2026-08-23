import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { EmptyState, ErrorBanner, ScoreBar, Spinner } from "../components/ui";
import type { DashboardStats } from "../types";

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .stats()
      .then((data) => {
        if (!cancelled) setStats(data);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) return <Spinner />;
  if (error) return <ErrorBanner message={error} />;
  if (!stats) return null;

  const hasActivity = stats.total_resumes > 0;

  return (
    <div>
      <div className="grid-stats">
        <div className="stat-card">
          <div className="stat-label">Resumes uploaded</div>
          <div className="stat-value">{stats.total_resumes}</div>
          <div className="stat-footnote">{stats.total_jobs} job description(s)</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Candidates screened</div>
          <div className="stat-value">{stats.candidates_screened}</div>
          <div className="stat-footnote">unique candidates with results</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Average match score</div>
          <div className="stat-value">
            {stats.average_match_score ? stats.average_match_score.toFixed(1) : "—"}
            <span style={{ fontSize: 14, color: "var(--text-muted)" }}> /10</span>
          </div>
          <div className="stat-footnote">across all screenings</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Shortlisted</div>
          <div className="stat-value" style={{ color: "var(--success)" }}>
            {stats.shortlisted_count}
          </div>
          <div className="stat-footnote">scored at or above threshold</div>
        </div>
      </div>

      {!hasActivity && (
        <div className="card card-pad">
          <EmptyState
            icon="🚀"
            title="Get started in three steps"
            hint="Upload a few resumes, create a job description, then run screening to see ranked, explainable results."
            action={
              <Link className="btn btn-primary" to="/upload">
                Upload resumes
              </Link>
            }
          />
        </div>
      )}

      {hasActivity && (
        <div className="card">
          <div className="card-pad" style={{ paddingBottom: 0 }}>
            <h2 className="section-title">Recent screening activity</h2>
            <p className="section-hint">
              The latest candidate/job match results recorded by the system.
            </p>
          </div>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Candidate</th>
                  <th>Job</th>
                  <th>Score</th>
                  <th>Status</th>
                  <th>Screened</th>
                </tr>
              </thead>
              <tbody>
                {stats.recent_activity.length === 0 && (
                  <tr>
                    <td colSpan={5}>
                      <EmptyState
                        icon="🗂"
                        title="No screening runs yet"
                        hint="Upload resumes and run a screening to populate the dashboard."
                      />
                    </td>
                  </tr>
                )}
                {stats.recent_activity.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <Link
                        to={`/screening?candidate=${item.candidate_id}`}
                        style={{ color: "inherit", textDecoration: "none" }}
                      >
                        <span className="cell-main">
                          {item.candidate_name ?? `Candidate #${item.candidate_id}`}
                        </span>
                      </Link>
                    </td>
                    <td>{item.job_title}</td>
                    <td>
                      <ScoreBar score={item.match_score} />
                    </td>
                    <td>
                      {item.shortlisted ? (
                        <span className="badge success">★ Shortlisted</span>
                      ) : (
                        <span className="badge neutral">Not shortlisted</span>
                      )}
                    </td>
                    <td className="cell-sub">
                      {new Date(item.screened_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
