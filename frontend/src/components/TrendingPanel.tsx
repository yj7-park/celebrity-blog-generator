import Card from "./Card";

interface Props {
  celebs: string[];
  selected: string;
  onSelect: (c: string) => void;
}

const RANK_COLORS = ["#f59e0b", "#9ca3af", "#b45309"];

export default function TrendingPanel({ celebs, selected, onSelect }: Props) {
  return (
    <Card title="🔥 트렌딩 연예인" badge={celebs.length}>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {celebs.map((c, i) => (
          <button
            key={c}
            onClick={() => onSelect(c)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "10px 14px",
              borderRadius: 8,
              border: selected === c ? "2px solid #6366f1" : "2px solid #e5e7eb",
              background: selected === c ? "#eef2ff" : "#f9fafb",
              cursor: "pointer",
              textAlign: "left",
              transition: "all 0.15s",
            }}
          >
            <span
              style={{
                width: 24,
                height: 24,
                borderRadius: "50%",
                background: RANK_COLORS[i] ?? "#d1d5db",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 12,
                fontWeight: 700,
                color: "#fff",
                flexShrink: 0,
              }}
            >
              {i + 1}
            </span>
            <span style={{ fontSize: 14, fontWeight: selected === c ? 600 : 400, color: "#111" }}>
              {c}
            </span>
          </button>
        ))}
      </div>
    </Card>
  );
}
