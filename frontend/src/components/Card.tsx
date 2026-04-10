import { ReactNode } from "react";

interface Props {
  title: string;
  children: ReactNode;
  badge?: string | number;
}

export default function Card({ title, children, badge }: Props) {
  return (
    <div
      style={{
        background: "#fff",
        border: "1px solid #e5e7eb",
        borderRadius: 12,
        padding: "20px 24px",
        marginBottom: 16,
        boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
        <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: "#111" }}>{title}</h3>
        {badge !== undefined && (
          <span
            style={{
              background: "#ede9fe",
              color: "#7c3aed",
              fontSize: 12,
              padding: "2px 8px",
              borderRadius: 99,
              fontWeight: 600,
            }}
          >
            {badge}
          </span>
        )}
      </div>
      {children}
    </div>
  );
}
