import { useEffect, useState } from "react";
import { api } from "../api/client";
import { ErrorBanner, Spinner } from "../components/ui";
import type { HealthInfo } from "../types";

export default function Settings() {
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .health()
      .then(setHealth)
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <div className="two-col">
      <div className="card card-pad">
        <h2 className="section-title">System status</h2>
        <p className="section-hint">
          Live status reported by the backend <code className="inline">/api/health</code>{" "}
          endpoint.
        </p>
        {!health && !error && <Spinner />}
        {error && (
          <ErrorBanner message={`${error} — the backend may not be running.`} />
        )}
        {health && (
          <>
            <div className="settings-row">
              <span className="settings-key">API server</span>
              <span className={`badge ${health.status === "ok" ? "success" : "danger"}`}>
                {health.status === "ok" ? "● Online" : "● Degraded"}
              </span>
            </div>
            <div className="settings-row">
              <span className="settings-key">Database</span>
              <span className={`badge ${health.database === "ok" ? "success" : "danger"}`}>
                {health.database}
              </span>
            </div>
            <div className="settings-row">
              <span className="settings-key">LLM provider</span>
              <span
                className={`badge ${
                  health.llm_provider.startsWith("mock")
                    ? "warning"
                    : health.llm_provider.includes("unconfigured")
                      ? "danger"
                      : "info"
                }`}
                data-testid="llm-provider"
              >
                {health.llm_provider}
              </span>
            </div>
          </>
        )}

        {health?.llm_provider === "mock" && (
          <div style={{ marginTop: 16 }}>
            <div className="info-banner" style={{ marginBottom: 0 }}>
              The app is using the built-in deterministic scorer. For real LLM
              reasoning and richer justifications, configure a provider in{" "}
              <code className="inline">backend/.env</code> (see the README's
              “LLM configuration” section) and restart the backend.
            </div>
          </div>
        )}
      </div>

      <div className="card card-pad">
        <h2 className="section-title">Configuration reference</h2>
        <p className="section-hint">
          All settings live in environment variables — secrets are never stored
          in the database or exposed to this UI.
        </p>
        <div className="settings-row">
          <span className="settings-key">
            <code className="inline">LLM_PROVIDER</code>
          </span>
          <span>mock | openai | anthropic</span>
        </div>
        <div className="settings-row">
          <span className="settings-key">
            <code className="inline">OPENAI_API_KEY</code>
          </span>
          <span>required for openai provider</span>
        </div>
        <div className="settings-row">
          <span className="settings-key">
            <code className="inline">OPENAI_BASE_URL</code>
          </span>
          <span>point at Groq / Ollama / etc.</span>
        </div>
        <div className="settings-row">
          <span className="settings-key">
            <code className="inline">ANTHROPIC_API_KEY</code>
          </span>
          <span>required for anthropic provider</span>
        </div>
        <div className="settings-row">
          <span className="settings-key">
            <code className="inline">DATABASE_URL</code>
          </span>
          <span>SQLite locally; PostgreSQL in production</span>
        </div>
        <div className="settings-row">
          <span className="settings-key">
            <code className="inline">SHORTLIST_THRESHOLD</code>
          </span>
          <span>default shortlist cutoff (1–10)</span>
        </div>
        <p className="section-hint" style={{ marginTop: 14 }}>
          API documentation (Swagger):{" "}
          <a href={apiDocsUrl()} target="_blank" rel="noreferrer">
            /api/docs
          </a>
        </p>
      </div>
    </div>
  );
}

function apiDocsUrl(): string {
  const base = import.meta.env.VITE_API_URL ?? "/api";
  if (base.startsWith("http")) {
    return `${base.replace(/\/$/, "")}/docs`;
  }
  return "/api/docs";
}
