import type { ReactNode } from "react";

export function Spinner({ label }: { label?: string }) {
  return (
    <div role="status" aria-label={label ?? "Loading"}>
      <div className="spinner" />
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="error-banner" role="alert">
      {message}
    </div>
  );
}

export function EmptyState({
  icon = "📄",
  title,
  hint,
  action,
}: {
  icon?: string;
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="icon" aria-hidden>
        {icon}
      </div>
      <div className="title">{title}</div>
      {hint && <div>{hint}</div>}
      {action && <div style={{ marginTop: 14 }}>{action}</div>}
    </div>
  );
}

const SCORE_COLORS: Array<{ min: number; color: string; label: string }> = [
  { min: 8, color: "#12b76a", label: "success" },
  { min: 7, color: "#2e90fa", label: "info" },
  { min: 5, color: "#f79009", label: "warning" },
  { min: 0, color: "#f04438", label: "danger" },
];

export function scoreBand(score: number) {
  return SCORE_COLORS.find((band) => score >= band.min) ?? SCORE_COLORS[3];
}

export function ScoreBar({ score }: { score: number }) {
  const band = scoreBand(score);
  return (
    <div
      className="score-cell"
      title={`Match score ${score.toFixed(1)} out of 10`}
    >
      <span className="score-num">{score.toFixed(1)}</span>
      <div className="score-bar">
        <div
          className="score-fill"
          style={{ width: `${score * 10}%`, background: band.color }}
        />
      </div>
    </div>
  );
}

export const RECOMMENDATION_LABELS: Record<string, string> = {
  strong_yes: "Strong yes",
  yes: "Yes",
  maybe: "Maybe",
  no: "No",
};

export function RecommendationBadge({
  recommendation,
}: {
  recommendation: string;
}) {
  const styles: Record<string, string> = {
    strong_yes: "success",
    yes: "info",
    maybe: "warning",
    no: "danger",
  };
  return (
    <span className={`badge ${styles[recommendation] ?? "neutral"}`}>
      {RECOMMENDATION_LABELS[recommendation] ?? recommendation}
    </span>
  );
}
