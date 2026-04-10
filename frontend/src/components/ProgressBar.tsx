interface Props {
  percent: number;
  step: string;
}

export default function ProgressBar({ percent, step }: Props) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontSize: 13, color: "#555" }}>{step}</span>
        <span style={{ fontSize: 13, color: "#555" }}>{percent}%</span>
      </div>
      <div style={{ background: "#e5e7eb", borderRadius: 8, height: 10, overflow: "hidden" }}>
        <div
          style={{
            height: "100%",
            width: `${percent}%`,
            background: "linear-gradient(90deg, #6366f1, #8b5cf6)",
            borderRadius: 8,
            transition: "width 0.4s ease",
          }}
        />
      </div>
    </div>
  );
}
