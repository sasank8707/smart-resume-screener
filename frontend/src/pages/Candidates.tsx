import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { notifyError, notifySuccess } from "../components/toaster";
import {
  EmptyState,
  ErrorBanner,
  Spinner,
} from "../components/ui";
import type { Candidate, CandidateDetail } from "../types";

export default function Candidates() {
  const [candidates, setCandidates] = useState<Candidate[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [skillFilter, setSkillFilter] = useState("");
  const [selected, setSelected] = useState<CandidateDetail | null>(null);

  const load = useCallback(() => {
    api
      .listCandidates({
        q: search || undefined,
        skill: skillFilter || undefined,
      })
      .then(setCandidates)
      .catch((err: Error) => setError(err.message));
  }, [search, skillFilter]);

  useEffect(() => {
    const timer = window.setTimeout(load, search || skillFilter ? 300 : 0);
    return () => window.clearTimeout(timer);
  }, [load, search, skillFilter]);

  async function openDetail(candidate: Candidate) {
    try {
      setSelected(await api.getCandidate(candidate.id));
    } catch (err) {
      notifyError(err instanceof Error ? err.message : "Could not load details");
    }
  }

  async function handleDelete(candidate: Candidate) {
    if (!window.confirm(`Delete candidate "${candidate.candidate_name ?? candidate.resume_filename}"?`))
      return;
    try {
      await api.deleteCandidate(candidate.id);
      setCandidates((prev) => prev?.filter((c) => c.id !== candidate.id) ?? null);
      if (selected?.id === candidate.id) setSelected(null);
      notifySuccess("Candidate deleted");
    } catch (err) {
      notifyError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  if (error) return <ErrorBanner message={error} />;
  if (!candidates) return <Spinner />;

  return (
    <div>
      <div className="card">
        <div className="filters-bar">
          <div className="grow">
            <input
              className="input"
              placeholder="Search by name or email…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="Search candidates"
            />
          </div>
          <div style={{ width: 200 }}>
            <input
              className="input"
              placeholder="Filter by skill…"
              value={skillFilter}
              onChange={(e) => setSkillFilter(e.target.value)}
              aria-label="Filter by skill"
            />
          </div>
        </div>

        {candidates.length === 0 ? (
          <EmptyState
            icon="👤"
            title={search || skillFilter ? "No matches" : "No candidates yet"}
            hint={
              search || skillFilter
                ? "Try a different search or clear the filters."
                : "Upload resumes to build your candidate pool."
            }
          />
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Candidate</th>
                  <th>Key skills</th>
                  <th>Experience</th>
                  <th>Source</th>
                  <th style={{ width: 130 }}></th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((candidate) => (
                  <tr
                    key={candidate.id}
                    className="row-click"
                    onClick={() => openDetail(candidate)}
                  >
                    <td>
                      <span className="cell-main">
                        {candidate.candidate_name ?? "Unknown name"}
                      </span>
                      <div className="cell-sub">{candidate.email ?? "no email"}</div>
                    </td>
                    <td style={{ maxWidth: 320 }}>
                      <div className="tag-list">
                        {candidate.skills.slice(0, 5).map((skill) => (
                          <span key={skill} className="tag">
                            {skill}
                          </span>
                        ))}
                        {candidate.skills.length > 5 && (
                          <span className="tag">+{candidate.skills.length - 5}</span>
                        )}
                        {candidate.skills.length === 0 && (
                          <span className="cell-sub">none detected</span>
                        )}
                      </div>
                    </td>
                    <td className="cell-sub">
                      {candidate.experience.length > 0
                        ? `${candidate.experience.length} role(s), latest: ${
                            candidate.experience[0]?.duration ?? "n/a"
                          }`
                        : "—"}
                    </td>
                    <td>
                      <span className={`badge ${candidate.file_type === "pdf" ? "danger" : "info"}`}>
                        {candidate.file_type.toUpperCase()}
                      </span>
                      <div className="cell-sub">{candidate.resume_filename}</div>
                    </td>
                    <td onClick={(e) => e.stopPropagation()}>
                      <button
                        className="btn btn-danger btn-sm"
                        onClick={() => handleDelete(candidate)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selected && (
        <CandidateDetailModal
          detail={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}

function CandidateDetailModal({
  detail,
  onClose,
}: {
  detail: CandidateDetail;
  onClose: () => void;
}) {
  return (
    <div
      className="modal-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Candidate details"
    >
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{detail.candidate_name ?? "Unknown candidate"}</h3>
          <button className="close-btn" aria-label="Close" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="modal-body">
          <dl className="kv-grid">
            <dt>Email</dt>
            <dd>{detail.email ?? "—"}</dd>
            <dt>Phone</dt>
            <dd>{detail.phone ?? "—"}</dd>
            <dt>File</dt>
            <dd>
              {detail.resume_filename} ({detail.file_type.toUpperCase()})
            </dd>
            <dt>Parsed</dt>
            <dd>{new Date(detail.created_at).toLocaleString()}</dd>
          </dl>

          {detail.summary && (
            <div className="detail-section">
              <h4>Summary</h4>
              <p style={{ margin: 0 }}>{detail.summary}</p>
            </div>
          )}

          <div className="detail-section">
            <h4>Skills ({detail.skills.length})</h4>
            <div className="tag-list">
              {detail.skills.map((skill) => (
                <span key={skill} className="tag">
                  {skill}
                </span>
              ))}
              {detail.skills.length === 0 && <span className="cell-sub">none detected</span>}
            </div>
          </div>

          <div className="detail-section">
            <h4>Experience</h4>
            {detail.experience.length === 0 && (
              <p className="cell-sub">No structured experience detected.</p>
            )}
            {detail.experience.map((entry, index) => (
              <div className="timeline-item" key={index} style={{ paddingBottom: index === detail.experience.length - 1 ? 0 : undefined }}>
                <div className="cell-main">{entry.role ?? "Role unknown"}</div>
                <div className="cell-sub">
                  {entry.organization ?? "Organization unknown"}
                  {entry.duration ? ` · ${entry.duration}` : ""}
                </div>
                <ul style={{ margin: "8px 0 4px", paddingLeft: 18, color: "var(--text-secondary)", fontSize: 13.2 }}>
                  {entry.responsibilities.slice(0, 4).map((resp, i) => (
                    <li key={i}>{resp}</li>
                  ))}
                </ul>
                {entry.technologies.length > 0 && (
                  <div className="tag-list">
                    {entry.technologies.slice(0, 8).map((tech) => (
                      <span key={tech} className="tag">
                        {tech}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="detail-section">
            <h4>Education</h4>
            {detail.education.length === 0 && (
              <p className="cell-sub">No structured education detected.</p>
            )}
            {detail.education.map((edu, index) => (
              <div key={index}>
                <span className="cell-main">{edu.degree ?? "Degree unknown"}</span>
                <div className="cell-sub">
                  {[edu.field, edu.institution]
                    .filter(Boolean)
                    .join(" · ") || "Institution unknown"}
                  {(edu.start_year || edu.end_year) &&
                    ` · ${edu.start_year ?? "?"}–${edu.end_year ?? "?"}`}
                </div>
              </div>
            ))}
          </div>

          {detail.certifications.length > 0 && (
            <div className="detail-section">
              <h4>Certifications</h4>
              <div className="tag-list">
                {detail.certifications.map((cert) => (
                  <span key={cert} className="tag">
                    {cert}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
