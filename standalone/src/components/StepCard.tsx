import { ReactNode } from "react";

export type StepStatus = "idle" | "running" | "done" | "error";

const STATUS_CONFIG: Record<StepStatus, { label: string; color: string; bg: string }> = {
  idle:    { label: "대기중", color: "#6b7280", bg: "#f3f4f6" },
  running: { label: "실행중", color: "#d97706", bg: "#fef3c7" },
  done:    { label: "완료",   color: "#059669", bg: "#d1fae5" },
  error:   { label: "오류",   color: "#dc2626", bg: "#fee2e2" },
};

interface Props {
  index: number;
  title: string;
  status: StepStatus;
  onRun?: () => void;
  canRun: boolean;
  progress?: { step: string; percent: number };
  error?: string;
  children?: ReactNode;
}

export default function StepCard({
  index,
  title,
  status,
  onRun,
  canRun,
  progress,
  error,
  children,
}: Props) {
  const cfg = STATUS_CONFIG[status];

  return (
    <div
      style={{
        background: "#fff",
        border: `1px solid ${status === "running" ? "#fbbf24" : status === "done" ? "#6ee7b7" : "#e5e7eb"}`,
        borderRadius: 14,
        padding: "20px 24px",
        marginBottom: 12,
        boxShadow: "0 1px 4px rgba(0,0,0,0.05)",
        transition: "border-color 0.3s",
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
        <div
          style={{
            width: 30,
            height: 30,
            borderRadius: "50%",
            background: status === "idle" ? "#e5e7eb" : "linear-gradient(135deg, #6366f1, #8b5cf6)",
            color: status === "idle" ? "#6b7280" : "#fff",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 700,
            fontSize: 14,
            flexShrink: 0,
          }}
        >
          {status === "done" ? "✓" : index}
        </div>
        <span style={{ fontWeight: 600, fontSize: 15, color: "#111", flex: 1 }}>{title}</span>
        <span
          style={{
            fontSize: 12,
            fontWeight: 600,
            padding: "3px 10px",
            borderRadius: 99,
            color: cfg.color,
            background: cfg.bg,
          }}
        >
          {cfg.label}
        </span>
        {canRun && status !== "running" && (
          <button
            onClick={onRun}
            style={{
              padding: "6px 16px",
              background: "linear-gradient(90deg, #6366f1, #8b5cf6)",
              color: "#fff",
              border: "none",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {status === "done" ? "재실행" : "실행"}
          </button>
        )}
        {status === "running" && (
          <span style={{ fontSize: 13, color: "#d97706" }}>⏳</span>
        )}
      </div>

      {/* Progress bar */}
      {status === "running" && progress && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#6b7280", marginBottom: 4 }}>
            <span>{progress.step}</span>
            <span>{progress.percent}%</span>
          </div>
          <div style={{ background: "#e5e7eb", borderRadius: 8, height: 6, overflow: "hidden" }}>
            <div
              style={{
                height: "100%",
                width: `${progress.percent}%`,
                background: "linear-gradient(90deg, #6366f1, #8b5cf6)",
                borderRadius: 8,
                transition: "width 0.3s ease",
              }}
            />
          </div>
        </div>
      )}

      {/* Error */}
      {status === "error" && error && (
        <p style={{ margin: "0 0 8px", fontSize: 13, color: "#dc2626" }}>⚠️ {error}</p>
      )}

      {/* Content */}
      {children && <div style={{ marginTop: 4 }}>{children}</div>}
    </div>
  );
}
