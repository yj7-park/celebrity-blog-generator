import Card from "./Card";

interface Props {
  items: Record<string, string>;
}

export default function ItemsPanel({ items }: Props) {
  const entries = Object.entries(items);
  return (
    <Card title="🛍️ 수집된 아이템" badge={entries.length}>
      {entries.length === 0 ? (
        <p style={{ margin: 0, fontSize: 13, color: "#9ca3af" }}>수집된 아이템이 없습니다.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {entries.map(([link, name], i) => (
            <div
              key={i}
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 8,
                padding: "8px 12px",
                background: "#f9fafb",
                borderRadius: 8,
                fontSize: 13,
              }}
            >
              <span style={{ color: "#6b7280", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {link || "(링크 텍스트 없음)"}
              </span>
              <span style={{ color: "#111", fontWeight: 500 }}>{name}</span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
