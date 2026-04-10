import type { CelebItem } from "../lib/types";

interface Props {
  items: CelebItem[];
}

const CATEGORY_COLORS: Record<string, { bg: string; color: string }> = {
  의류: { bg: "#dbeafe", color: "#1d4ed8" },
  신발: { bg: "#fef3c7", color: "#92400e" },
  가방: { bg: "#fce7f3", color: "#be185d" },
  액세서리: { bg: "#d1fae5", color: "#065f46" },
  화장품: { bg: "#ede9fe", color: "#7c3aed" },
  식품: { bg: "#ffedd5", color: "#c2410c" },
  기타: { bg: "#f3f4f6", color: "#4b5563" },
};

function getCategoryStyle(category: string) {
  return (
    CATEGORY_COLORS[category] ?? { bg: "#f3f4f6", color: "#4b5563" }
  );
}

export default function ItemsPanel({ items }: Props) {
  if (items.length === 0) {
    return (
      <div
        style={{
          background: "#f9fafb",
          borderRadius: 10,
          padding: "20px",
          textAlign: "center",
          color: "#9ca3af",
          fontSize: 14,
        }}
      >
        수집된 아이템이 없습니다.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {items.map((item, i) => {
        const catStyle = getCategoryStyle(item.category);
        return (
          <div
            key={i}
            style={{
              background: "#fff",
              border: "1px solid #e5e7eb",
              borderRadius: 12,
              padding: "14px 16px",
              display: "flex",
              gap: 14,
              alignItems: "flex-start",
            }}
          >
            {/* 이미지 */}
            {item.image_urls && item.image_urls[0] ? (
              <img
                src={item.image_urls[0]}
                alt={item.product_name}
                style={{
                  width: 72,
                  height: 72,
                  borderRadius: 8,
                  objectFit: "cover",
                  flexShrink: 0,
                  background: "#f3f4f6",
                }}
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = "none";
                }}
              />
            ) : (
              <div
                style={{
                  width: 72,
                  height: 72,
                  borderRadius: 8,
                  background: "#f3f4f6",
                  flexShrink: 0,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 24,
                }}
              >
                🛍️
              </div>
            )}

            {/* 정보 */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <span
                  style={{
                    background: catStyle.bg,
                    color: catStyle.color,
                    fontSize: 11,
                    padding: "2px 8px",
                    borderRadius: 99,
                    fontWeight: 600,
                    flexShrink: 0,
                  }}
                >
                  {item.category}
                </span>
                <span
                  style={{
                    fontSize: 13,
                    fontWeight: 600,
                    color: "#111",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {item.product_name}
                </span>
              </div>

              {item.keywords && item.keywords.length > 0 && (
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginBottom: 6 }}>
                  {item.keywords.slice(0, 5).map((kw, j) => (
                    <span
                      key={j}
                      style={{
                        fontSize: 11,
                        color: "#6b7280",
                        background: "#f3f4f6",
                        padding: "1px 6px",
                        borderRadius: 4,
                      }}
                    >
                      #{kw}
                    </span>
                  ))}
                </div>
              )}

              <div style={{ fontSize: 12, color: "#9ca3af" }}>
                출처: {item.source_title || item.source_url}
              </div>
            </div>

            {/* 구매 링크 */}
            {item.link_url && (
              <a
                href={item.link_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  flexShrink: 0,
                  padding: "6px 12px",
                  background: "#ede9fe",
                  color: "#7c3aed",
                  borderRadius: 8,
                  fontSize: 12,
                  fontWeight: 600,
                  textDecoration: "none",
                  whiteSpace: "nowrap",
                }}
              >
                구매 링크
              </a>
            )}
          </div>
        );
      })}
    </div>
  );
}
