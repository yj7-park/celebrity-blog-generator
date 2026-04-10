import type { CelebItem } from "../lib/types";
import Card from "./Card";

interface Props {
  items: CelebItem[];
}

const CATEGORY_COLORS: Record<string, string> = {
  가방: "#f59e0b", 신발: "#10b981", 의류: "#6366f1",
  뷰티: "#ec4899", 식품: "#22c55e", 생활: "#0ea5e9",
  액세서리: "#a855f7", 기타: "#9ca3af",
};

export default function ItemsPanel({ items }: Props) {
  if (items.length === 0) {
    return (
      <Card title="🛍️ 추출된 아이템" badge={0}>
        <p style={{ margin: 0, fontSize: 13, color: "#9ca3af" }}>수집된 아이템이 없습니다.</p>
      </Card>
    );
  }

  return (
    <Card title="🛍️ 추출된 아이템" badge={items.length}>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {items.map((item, i) => {
          const catColor = CATEGORY_COLORS[item.category] ?? "#9ca3af";
          return (
            <div
              key={i}
              style={{
                display: "grid",
                gridTemplateColumns: item.image_urls.length > 0 ? "56px 1fr" : "1fr",
                gap: 10,
                padding: "10px 12px",
                background: "#f9fafb",
                borderRadius: 10,
                border: "1px solid #e5e7eb",
              }}
            >
              {item.image_urls.length > 0 && (
                <img
                  src={item.image_urls[0]}
                  alt={item.product_name}
                  style={{
                    width: 56, height: 56, objectFit: "cover",
                    borderRadius: 6, flexShrink: 0,
                  }}
                  onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                />
              )}
              <div style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 0 }}>
                {/* Row 1: category badge + celeb + product name */}
                <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                  <span
                    style={{
                      background: catColor, color: "#fff", fontSize: 11,
                      fontWeight: 700, padding: "2px 7px", borderRadius: 99,
                      flexShrink: 0,
                    }}
                  >
                    {item.category}
                  </span>
                  <span style={{ fontSize: 12, color: "#6366f1", fontWeight: 600, flexShrink: 0 }}>
                    {item.celeb}
                  </span>
                  <span
                    style={{
                      fontSize: 13, fontWeight: 500, color: "#111",
                      overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                    }}
                  >
                    {item.product_name}
                  </span>
                </div>
                {/* Row 2: keywords + link */}
                <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                  {item.keywords.slice(0, 3).map((kw, ki) => (
                    <span
                      key={ki}
                      style={{
                        background: "#e0e7ff", color: "#4338ca",
                        fontSize: 11, padding: "1px 6px", borderRadius: 99,
                      }}
                    >
                      {kw}
                    </span>
                  ))}
                  {item.link_url && (
                    <a
                      href={item.link_url}
                      target="_blank"
                      rel="noreferrer"
                      style={{ fontSize: 11, color: "#6366f1", textDecoration: "none", marginLeft: "auto" }}
                    >
                      🛒 구매링크
                    </a>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
