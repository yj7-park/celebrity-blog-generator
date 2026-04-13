import { useState } from "react";
import type { CelebItem } from "../lib/types";

/** Proxy pstatic.net / blogfiles images through the backend to avoid CORS. */
function proxyImageUrl(url: string): string {
  if (!url) return url;
  const PROXIED = ["pstatic.net", "blogfiles.naver.net", "daumcdn.net"];
  if (PROXIED.some((d) => url.includes(d))) {
    return `/api/proxy/image?url=${encodeURIComponent(url)}`;
  }
  return url;
}

interface Props {
  items: CelebItem[];
  /** Called when the user picks a new candidate image URL for an item. */
  onUpdateItem?: (index: number, newImageUrl: string) => Promise<void>;
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
  return CATEGORY_COLORS[category] ?? { bg: "#f3f4f6", color: "#4b5563" };
}

export default function ItemsPanel({ items, onUpdateItem }: Props) {
  const [openPickerIdx, setOpenPickerIdx] = useState<number | null>(null);
  const [loadingIdx, setLoadingIdx] = useState<number | null>(null);

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

  const handleSelectImage = async (itemIndex: number, url: string) => {
    if (!onUpdateItem) return;
    setLoadingIdx(itemIndex);
    setOpenPickerIdx(null);
    try {
      await onUpdateItem(itemIndex, url);
    } finally {
      setLoadingIdx(null);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {items.map((item, i) => {
        const catStyle = getCategoryStyle(item.category);
        const candidates = item.candidate_image_urls ?? [];
        const hasMultiple = candidates.length > 1 || (candidates.length === 1 && candidates[0] !== item.image_urls?.[0]);
        const isPickerOpen = openPickerIdx === i;
        const isLoading = loadingIdx === i;

        // All candidate URLs including the current main image
        const allCandidates = Array.from(
          new Set([...(item.image_urls ?? []), ...candidates])
        );

        return (
          <div
            key={i}
            style={{
              background: "#fff",
              border: "1px solid #e5e7eb",
              borderRadius: 12,
              padding: "14px 16px",
              display: "flex",
              flexDirection: "column",
              gap: 0,
            }}
          >
            {/* Main row */}
            <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
              {/* 이미지 */}
              <div style={{ position: "relative", flexShrink: 0 }}>
                {item.image_urls && item.image_urls[0] ? (
                  <img
                    src={proxyImageUrl(item.image_urls[0])}
                    alt={item.product_name}
                    style={{
                      width: 72,
                      height: 72,
                      borderRadius: 8,
                      objectFit: "cover",
                      background: "#f3f4f6",
                      opacity: isLoading ? 0.4 : 1,
                      transition: "opacity 0.2s",
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
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 24,
                    }}
                  >
                    🛍️
                  </div>
                )}

                {/* Loading spinner overlay */}
                {isLoading && (
                  <div
                    style={{
                      position: "absolute",
                      inset: 0,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 18,
                    }}
                  >
                    ⏳
                  </div>
                )}
              </div>

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

              {/* 오른쪽 버튼 영역 */}
              <div style={{ display: "flex", flexDirection: "column", gap: 6, flexShrink: 0, alignItems: "flex-end" }}>
                {item.link_url && (
                  <a
                    href={item.link_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
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

                {/* Image picker toggle — only when callback is provided */}
                {onUpdateItem && allCandidates.length > 1 && (
                  <button
                    onClick={() => setOpenPickerIdx(isPickerOpen ? null : i)}
                    disabled={isLoading}
                    style={{
                      padding: "5px 10px",
                      background: isPickerOpen ? "#d1fae5" : "#f3f4f6",
                      color: isPickerOpen ? "#065f46" : "#374151",
                      border: "1px solid " + (isPickerOpen ? "#a7f3d0" : "#d1d5db"),
                      borderRadius: 8,
                      fontSize: 11,
                      fontWeight: 600,
                      cursor: isLoading ? "not-allowed" : "pointer",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {isPickerOpen ? "닫기" : `이미지 선택 (${allCandidates.length})`}
                  </button>
                )}
              </div>
            </div>

            {/* Image picker tray */}
            {isPickerOpen && onUpdateItem && (
              <div
                style={{
                  marginTop: 12,
                  padding: "10px 0 4px",
                  borderTop: "1px solid #f3f4f6",
                }}
              >
                <div
                  style={{
                    fontSize: 11,
                    color: "#6b7280",
                    fontWeight: 600,
                    marginBottom: 8,
                    letterSpacing: "0.04em",
                    textTransform: "uppercase",
                  }}
                >
                  후보 이미지 선택
                </div>
                <div
                  style={{
                    display: "flex",
                    gap: 8,
                    overflowX: "auto",
                    paddingBottom: 6,
                  }}
                >
                  {allCandidates.map((url, ci) => {
                    const isCurrent = url === item.image_urls?.[0];
                    return (
                      <div
                        key={ci}
                        onClick={() => handleSelectImage(i, url)}
                        style={{
                          flexShrink: 0,
                          cursor: "pointer",
                          borderRadius: 8,
                          border: isCurrent
                            ? "2px solid #6366f1"
                            : "2px solid transparent",
                          outline: isCurrent ? "none" : "1px solid #e5e7eb",
                          overflow: "hidden",
                          transition: "border-color 0.15s, transform 0.1s",
                        }}
                        title={isCurrent ? "현재 선택됨" : "이 이미지 사용"}
                        onMouseEnter={(e) => {
                          if (!isCurrent)
                            (e.currentTarget as HTMLDivElement).style.borderColor = "#a5b4fc";
                        }}
                        onMouseLeave={(e) => {
                          if (!isCurrent)
                            (e.currentTarget as HTMLDivElement).style.borderColor = "transparent";
                        }}
                      >
                        <img
                          src={proxyImageUrl(url)}
                          alt={`후보 ${ci + 1}`}
                          style={{
                            width: 80,
                            height: 80,
                            objectFit: "cover",
                            display: "block",
                          }}
                          onError={(e) => {
                            (e.target as HTMLImageElement).parentElement!.style.display = "none";
                          }}
                        />
                        {isCurrent && (
                          <div
                            style={{
                              background: "#6366f1",
                              color: "#fff",
                              fontSize: 9,
                              fontWeight: 700,
                              textAlign: "center",
                              padding: "2px 0",
                              letterSpacing: "0.05em",
                            }}
                          >
                            현재
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
