import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { notifyError, notifySuccess } from "../components/toaster";
import { EmptyState, ErrorBanner, Spinner } from "../components/ui";
import type { JobDescription, JobRequirements } from "../types";

const SAMPLE_JD = `Senior Python Developer

We are building a data-driven platform and need an experienced backend engineer.

Responsibilities:
- Design and ship reliable REST APIs
- Improve system performance and observability
- Mentor junior engineers

Requirements:
- 5+ years of professional software engineering experience
- Strong Python skills with FastAPI or Django
- Solid SQL knowledge (PostgreSQL preferred)
- Experience with Docker

Nice-to-have:
- Kubernetes in production
- AWS cloud experience`;

export default function JobDescriptions() {
  const [jobs, setJobs] = useState<JobDescription[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<JobDescription | null>(null);
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();

  const load = useCallback(() => {
    api
      .listJobs()
      .then(setJobs)
      .catch((err: Error) => setError(err.message));
  }, []);

  useEffect(load, [load]);

  async function handleDelete(job: JobDescription) {
    if (!window.confirm(`Delete "${job.title}"? Screening results for it will also be removed.`))
      return;
    try {
      await api.deleteJob(job.id);
      notifySuccess("Job description deleted");
      load();
    } catch (err) {
      notifyError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  if (error) return <ErrorBanner message={error} />;
  if (!jobs) return <Spinner />;

  return (
    <div>
      <div className="page-head">
        <div>
          <h2 className="section-title">Your job descriptions</h2>
          <p>
            Requirements (skills, experience and education) are extracted
            automatically when you save or edit a description.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setCreating(true)}>
          + New job description
        </button>
      </div>

      {jobs.length === 0 ? (
        <div className="card">
          <EmptyState
            icon="☰"
            title="No job descriptions yet"
            hint="Create one to start screening candidates against it."
            action={
              <button className="btn btn-primary" onClick={() => setCreating(true)}>
                Create your first job
              </button>
            }
          />
        </div>
      ) : (
        <div className="card">
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Required skills</th>
                  <th>Experience</th>
                  <th style={{ width: 210 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id}>
                    <td>
                      <span className="cell-main">{job.title}</span>
                      <div className="cell-sub">
                        Updated {new Date(job.updated_at).toLocaleDateString()}
                      </div>
                    </td>
                    <td style={{ maxWidth: 340 }}>
                      <div className="tag-list">
                        {(job.requirements?.required_skills ?? [])
                          .slice(0, 6)
                          .map((skill) => (
                            <span key={skill} className="tag required">
                              {skill}
                            </span>
                          ))}
                        {(job.requirements?.required_skills ?? []).length === 0 && (
                          <span className="cell-sub">none detected</span>
                        )}
                      </div>
                    </td>
                    <td className="cell-sub">
                      {job.requirements?.experience_expectations ?? "—"}
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() =>
                            navigate(`/screening?job=${job.id}`)
                          }
                        >
                          Screen
                        </button>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => setEditing(job)}
                        >
                          Edit
                        </button>
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => handleDelete(job)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {(creating || editing) && (
        <JobFormModal
          job={editing}
          onClose={() => {
            setCreating(false);
            setEditing(null);
          }}
          onSaved={(saved) => {
            setCreating(false);
            setEditing(null);
            notifySuccess(
              editing ? "Job description updated" : "Job description created",
            );
            if (!editing) {
              navigate(`/screening?job=${saved.id}`);
            } else {
              load();
            }
          }}
        />
      )}
    </div>
  );
}

function JobFormModal({
  job,
  onClose,
  onSaved,
}: {
  job: JobDescription | null;
  onClose: () => void;
  onSaved: (job: JobDescription) => void;
}) {
  const [title, setTitle] = useState(job?.title ?? "");
  const [text, setText] = useState(job?.description_text ?? "");
  const [requirements, setRequirements] = useState<JobRequirements | null>(
    job?.requirements ?? null,
  );
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function save() {
    setSaving(true);
    setFormError(null);
    try {
      const saved = job
        ? await api.updateJob(job.id, { title, description_text: text })
        : await api.createJob({ title, description_text: text });
      setRequirements(saved.requirements);
      onSaved(saved);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  const valid = title.trim().length >= 2 && text.trim().length >= 30;

  return (
    <div
      className="modal-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={job ? "Edit job description" : "Create job description"}
    >
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{job ? "Edit job description" : "New job description"}</h3>
          <button className="close-btn" aria-label="Close" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="modal-body">
          <label className="field-label" htmlFor="job-title">
            Title
          </label>
          <input
            id="job-title"
            className="input"
            value={title}
            placeholder="e.g. Senior Backend Engineer"
            onChange={(e) => setTitle(e.target.value)}
          />
          <label className="field-label" htmlFor="job-text">
            Description{" "}
            <span className="settings-key">(minimum 30 characters)</span>
          </label>
          <textarea
            id="job-text"
            className="textarea"
            rows={10}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={"Paste the full job description here…\n\nTip: use 'Requirements:' and 'Nice-to-have:' sections for the best extraction."}
          />
          {!job && text.length === 0 && (
            <button
              className="btn btn-ghost btn-sm"
              style={{ marginTop: 8 }}
              onClick={() => setText(SAMPLE_JD)}
            >
              Insert example description
            </button>
          )}
          {requirements && (
            <div className="info-banner" style={{ marginTop: 14 }}>
              Extracted requirements preview:{" "}
              {[...(requirements.required_skills ?? [])]
                .slice(0, 8)
                .join(", ") || "no explicit skills detected"}
            </div>
          )}
          {formError && (
            <div style={{ marginTop: 12 }}>
              <ErrorBanner message={formError} />
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            disabled={!valid || saving}
            onClick={save}
          >
            {saving ? "Saving…" : job ? "Save changes" : "Create & continue"}
          </button>
        </div>
      </div>
    </div>
  );
}
