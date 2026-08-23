import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { notifyError, notifySuccess } from "../components/toaster";
import { EmptyState, ErrorBanner } from "../components/ui";
import type { UploadResponse } from "../types";

const ACCEPT = ".pdf,.txt,.text,.md";
const MAX_MB = 10;

export default function UploadResumes() {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function addFiles(incoming: FileList | null) {
    if (!incoming) return;
    const accepted: File[] = [];
    for (const file of Array.from(incoming)) {
      const okType = /\.(pdf|txt|text|md)$/i.test(file.name);
      if (!okType) {
        notifyError(`${file.name}: only PDF and TXT files are supported.`);
        continue;
      }
      if (file.size > MAX_MB * 1024 * 1024) {
        notifyError(`${file.name}: exceeds the ${MAX_MB} MB limit.`);
        continue;
      }
      accepted.push(file);
    }
    setFiles((prev) => {
      const names = new Set(prev.map((f) => f.name + f.size));
      return [...prev, ...accepted.filter((f) => !names.has(f.name + f.size))];
    });
    setError(null);
  }

  async function handleUpload() {
    if (files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      const response = await api.uploadResumes(files);
      setResult(response);
      setFiles([]);
      if (inputRef.current) inputRef.current.value = "";
      if (response.uploaded.length > 0) {
        notifySuccess(
          `Parsed ${response.uploaded.length} resume(s)` +
            (response.errors.length
              ? `, ${response.errors.length} failed`
              : " successfully"),
        );
      }
      if (response.errors.length > 0 && response.uploaded.length === 0) {
        setError(response.errors.map((e) => `${e.filename}: ${e.error}`).join(" · "));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="two-col">
      <div className="card card-pad">
        <h2 className="section-title">Add resumes</h2>
        <p className="section-hint">
          PDF or TXT, up to {MAX_MB} MB each. Select several files to process a
          full batch in one go.
        </p>

        <div
          className={`dropzone${dragOver ? " dragover" : ""}`}
          role="button"
          tabIndex={0}
          aria-label="Choose resume files"
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            addFiles(e.dataTransfer.files);
          }}
        >
          <div className="big">Drag & drop resumes here</div>
          <div>
            or click to browse — .pdf, .txt · multiple files supported
          </div>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          multiple
          hidden
          data-testid="file-input"
          onChange={(e) => addFiles(e.target.files)}
        />

        {files.length > 0 && (
          <div style={{ marginTop: 16 }}>
            {files.map((file) => (
              <div className="file-chip" key={file.name + file.size}>
                <span>
                  📄 {file.name}{" "}
                  <span className="cell-sub">
                    ({(file.size / 1024).toFixed(0)} KB)
                  </span>
                </span>
                <button
                  className="close-btn"
                  aria-label={`Remove ${file.name}`}
                  onClick={() =>
                    setFiles((prev) =>
                      prev.filter((f) => f.name + f.size !== file.name + file.size),
                    )
                  }
                >
                  ×
                </button>
              </div>
            ))}
            <button
              className="btn btn-primary"
              onClick={handleUpload}
              disabled={uploading}
              data-testid="start-upload"
            >
              {uploading ? "Processing…" : `Parse ${files.length} resume(s)`}
            </button>
          </div>
        )}

        {error && (
          <div style={{ marginTop: 14 }}>
            <ErrorBanner message={error} />
          </div>
        )}
        {uploading && (
          <p className="section-hint" style={{ marginTop: 12 }}>
            Extracting text and parsing structured profiles… this can take a few
            seconds per resume.
          </p>
        )}
      </div>

      <div className="card card-pad">
        <h2 className="section-title">Last upload result</h2>
        {!result && (
          <p className="section-hint">
            Parsed candidates will appear here after your next upload.
          </p>
        )}
        {result && result.uploaded.length === 0 && result.errors.length === 0 && (
          <EmptyState title="Nothing processed" />
        )}
        {result?.uploaded.map((candidate) => (
          <div className="file-chip" key={candidate.id}>
            <span>
              ✅{" "}
              <Link to="/candidates" style={{ color: "inherit" }}>
                {candidate.candidate_name ?? candidate.resume_filename}
              </Link>{" "}
              <span className="cell-sub">
                {candidate.skills.length} skills ·{" "}
                {candidate.experience.length} experience entries
              </span>
            </span>
            <span className={`badge ${candidate.file_type === "pdf" ? "danger" : "info"}`}>
              {candidate.file_type.toUpperCase()}
            </span>
          </div>
        ))}
        {result?.errors.map((err) => (
          <div className="file-chip" key={err.filename}>
            <span>⚠️ {err.filename}</span>
            <span className="badge danger">{err.error}</span>
          </div>
        ))}
        {result && result.uploaded.length > 0 && (
          <Link to="/screening" className="btn btn-ghost btn-sm" style={{ marginTop: 8 }}>
            Continue to screening →
          </Link>
        )}
      </div>
    </div>
  );
}
