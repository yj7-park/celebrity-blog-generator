import { useState, useEffect } from "react";
import type { CelebItem, ItemImageAnalysis, WatermarkRegion, SimilarImageSearchResult } from "../lib/types";

async function fetchSimilarImages(item: CelebItem, origUrl: string, regions: WatermarkRegion[]): Promise<SimilarImageSearchResult> {
  const res = await fetch("/api/pipeline/find-similar-images", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      celeb: item.celeb,
      product_name: item.product_name,
      keywords: item.keywords,
      orig_url: origUrl,
      watermark_regions: regions,
      max_posts: 8,
    }),
  });
  if (!res.ok) return { processed_path: null, similar_urls: [], blog_urls: [], new_sources: [], method: "none" };
  return res.json();
}

/** Proxy pstatic.net / blogfiles images through the backend to avoid CORS.
 *  Also routes local processed-image file paths through the backend. */
function proxyImageUrl(url: string): string {
  if (!url) return url;
  // Local file path (Windows or Unix absolute) from process-image endpoint
  if (!url.startsWith("http") && !url.startsWith("/api")) {
    const filename = url.replace(/\\/g, "/").split("/").pop() ?? "";
    return `/api/proxy/processed/${encodeURIComponent(filename)}`;
  }
  const PROXIED = ["pstatic.net", "blogfiles.naver.net", "daumcdn.net"];
  if (PROXIED.some((d) => url.includes(d))) {
    return `/api/proxy/image?url=${encodeURIComponent(url)}`;
  }
  return url;
}

interface SimilarSearchState {
  loading: boolean;
  result: SimilarImageSearchResult | null;
}

interface Props {
  items: CelebItem[];
  analyses?: ItemImageAnalysis[];
  simResults?: Record<number, { loading: boolean; result: SimilarImageSearchResult | null }>;
  onUpdateItem?: (index: number, newImageUrl: string) => Promise<void>;
  onRemoveWatermark?: (index: number, url: string, regions: WatermarkRegion[]) => Promise<void>;
  onSimSearch?: (itemIndex: number, item: CelebItem, origUrl: string, regions: WatermarkRegion[]) => void;
}

const CATEGORY_COLORS: Record<string, { bg: string; color: string }> = {
  의류:    { bg: "#dbeafe", color: "#1d4ed8" },
  신발:    { bg: "#fef3c7", color: "#92400e" },
  가방:    { bg: "#fce7f3", color: "#be185d" },
  액세서리:{ bg: "#d1fae5", color: "#065f46" },
  화장품:  { bg: "#ede9fe", color: "#7c3aed" },
  식품:    { bg: "#ffedd5", color: "#c2410c" },
  기타:    { bg: "#f3f4f6", color: "#4b5563" },
};

const ISSUE_META: Record<string, { label: string; bg: string; color: string }> = {
  watermark:   { label: "워터마크",     bg: "#fef3c7", color: "#92400e" },
  mismatch:    { label: "이미지 불일치", bg: "#fee2e2", color: "#dc2626" },
  low_quality: { label: "저품질",       bg: "#f3f4f6", color: "#4b5563" },
  cropped:     { label: "잘림",         bg: "#dbeafe", color: "#1d4ed8" },
};

function getCategoryStyle(cat: string) {
  return CATEGORY_COLORS[cat] ?? { bg: "#f3f4f6", color: "#4b5563" };
}

function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const [bg, color] =
    score >= 0.8
      ? ["#d1fae5", "#065f46"]
      : score >= 0.65
      ? ["#fef3c7", "#92400e"]
      : ["#fee2e2", "#dc2626"];
  return (
    <span
      style={{
        fontSize: 11,
        fontWeight: 700,
        background: bg,
        color,
        padding: "2px 7px",
        borderRadius: 99,
        flexShrink: 0,
      }}
      title="AI 관련성 점수"
    >
      {pct}%
    </span>
  );
}

function IssueTags({ issues }: { issues: string[] }) {
  if (!issues.length) return null;
  return (
    <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: 4 }}>
      {issues.map((issue) => {
        const meta = ISSUE_META[issue] ?? { label: issue, bg: "#f3f4f6", color: "#4b5563" };
        return (
          <span
            key={issue}
            style={{
              fontSize: 10,
              fontWeight: 600,
              background: meta.bg,
              color: meta.color,
              padding: "1px 6px",
              borderRadius: 99,
            }}
          >
            {meta.label}
          </span>
        );
      })}
    </div>
  );
}

export default function ItemsPanel({ items, analyses, simResults, onUpdateItem, onRemoveWatermark, onSimSearch }: Props) {
  const [openPickerIdx, setOpenPickerIdx]         = useState<number | null>(null);
  const [loadingIdx, setLoadingIdx]               = useState<number | null>(null);
  const [wmLoadingKey, setWmLoadingKey]           = useState<string | null>(null);
  const [customUrls, setCustomUrls]               = useState<Record<number, string>>({});
  const [zoomedUrl, setZoomedUrl]                 = useState<string | null>(null);
  // similar image search state — merge external (from parent) + local manual triggers
  const [simSearch, setSimSearch]                 = useState<Record<number, SimilarSearchState>>({});

  // Sync external simResults into local simSearch state
  useEffect(() => {
    if (!simResults) return;
    setSimSearch((prev) => {
      const merged = { ...prev };
      for (const [idxStr, state] of Object.entries(simResults)) {
        merged[Number(idxStr)] = state;
      }
      return merged;
    });
  }, [simResults]);

  if (items.length === 0) {
    return (
      <div style={{ background: "#f9fafb", borderRadius: 10, padding: 20,
                    textAlign: "center", color: "#9ca3af", fontSize: 14 }}>
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

  const handleCustomUrl = async (itemIndex: number) => {
    const url = customUrls[itemIndex]?.trim();
    if (!url) return;
    await handleSelectImage(itemIndex, url);
    setCustomUrls((prev) => ({ ...prev, [itemIndex]: "" }));
  };

  const handleRemoveWatermark = async (
    itemIndex: number,
    url: string,
    regions: WatermarkRegion[]
  ) => {
    if (!onRemoveWatermark) return;
    const key = `${itemIndex}_${url}`;
    setWmLoadingKey(key);
    try {
      await onRemoveWatermark(itemIndex, url, regions);
    } finally {
      setWmLoadingKey(null);
    }
  };

  const handleSimilarSearch = (
    itemIndex: number,
    item: CelebItem,
    origUrl: string,
    regions: WatermarkRegion[],
  ) => {
    if (onSimSearch) {
      // Delegate to parent (PipelinePage manages state + auto-applies results)
      onSimSearch(itemIndex, item, origUrl, regions);
    } else {
      // Standalone mode (DashboardPage): manage locally
      setSimSearch((prev) => ({ ...prev, [itemIndex]: { loading: true, result: null } }));
      fetchSimilarImages(item, origUrl, regions)
        .then((result) => {
          setSimSearch((prev) => ({ ...prev, [itemIndex]: { loading: false, result } }));
          if (result.processed_path && onUpdateItem) {
            onUpdateItem(itemIndex, result.processed_path).catch(() => {});
          }
        })
        .catch(() => {
          setSimSearch((prev) => ({ ...prev, [itemIndex]: { loading: false, result: null } }));
        });
    }
  };

  return (
    <>
    {/* ── Zoom modal ──────────────────────────────────────────────────── */}
    {zoomedUrl && (
      <div
        onClick={() => setZoomedUrl(null)}
        style={{
          position: "fixed", inset: 0,
          background: "rgba(0,0,0,0.88)",
          display: "flex", alignItems: "center", justifyContent: "center",
          zIndex: 9999, cursor: "zoom-out",
        }}
      >
        <img
          src={proxyImageUrl(zoomedUrl)}
          alt="확대 보기"
          onClick={(e) => e.stopPropagation()}
          style={{
            maxWidth: "90vw", maxHeight: "90vh",
            objectFit: "contain", borderRadius: 10,
            boxShadow: "0 8px 40px rgba(0,0,0,0.6)",
            cursor: "default",
          }}
        />
        <button
          onClick={() => setZoomedUrl(null)}
          style={{
            position: "fixed", top: 20, right: 24,
            background: "rgba(255,255,255,0.15)", border: "none",
            color: "#fff", fontSize: 22, borderRadius: "50%",
            width: 40, height: 40, cursor: "pointer",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}
        >
          ✕
        </button>
      </div>
    )}

    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {items.map((item, i) => {
        const catStyle     = getCategoryStyle(item.category);
        const analysis     = analyses?.find((a) => a.item_index === i);
        const isPickerOpen = openPickerIdx === i;
        const isLoading    = loadingIdx === i;
        const simState     = simSearch[i] ?? { loading: false, result: null };

        // Merge image_urls + candidate_image_urls, deduplicated
        const allCandidates = Array.from(
          new Set([...(item.image_urls ?? []), ...(item.candidate_image_urls ?? [])])
        );

        // Build score map: url → CandidateScore
        const scoreMap = Object.fromEntries(
          (analysis?.candidates ?? []).map((c) => [c.url, c])
        );

        // Current displayed image
        const currentUrl = item.processed_image_path || item.image_urls?.[0] || "";

        return (
          <div
            key={i}
            style={{
              background: "#fff",
              border: `1px solid ${analysis?.needs_review ? "#fbbf24" : "#e5e7eb"}`,
              borderRadius: 12,
              padding: "14px 16px",
              display: "flex",
              flexDirection: "column",
              gap: 0,
            }}
          >
            {/* ── Main row ─────────────────────────────────────────────── */}
            <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>

              {/* Thumbnail */}
              <div style={{ position: "relative", flexShrink: 0 }}>
                {currentUrl ? (
                  <img
                    src={proxyImageUrl(currentUrl)}
                    alt={item.product_name}
                    onClick={() => setZoomedUrl(currentUrl)}
                    style={{
                      width: 80, height: 80,
                      borderRadius: 8, objectFit: "cover",
                      background: "#f3f4f6",
                      opacity: isLoading ? 0.4 : 1,
                      transition: "opacity 0.2s",
                      cursor: "zoom-in",
                    }}
                    onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                  />
                ) : (
                  <div style={{
                    width: 80, height: 80, borderRadius: 8,
                    background: "#f3f4f6", display: "flex",
                    alignItems: "center", justifyContent: "center", fontSize: 28,
                  }}>
                    🛍️
                  </div>
                )}
                {isLoading && (
                  <div style={{
                    position: "absolute", inset: 0,
                    display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20,
                  }}>
                    ⏳
                  </div>
                )}
                {/* Processed badge */}
                {item.processed_image_path && (
                  <div style={{
                    position: "absolute", bottom: 0, right: 0,
                    background: "#7c3aed", borderRadius: "0 0 8px 0",
                    padding: "1px 4px", fontSize: 9, color: "#fff", fontWeight: 700,
                  }}>
                    처리됨
                  </div>
                )}
              </div>

              {/* Info */}
              <div style={{ flex: 1, minWidth: 0 }}>
                {/* Category + product name + score badge */}
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4, flexWrap: "wrap" }}>
                  <span style={{
                    background: catStyle.bg, color: catStyle.color,
                    fontSize: 11, padding: "2px 8px", borderRadius: 99, fontWeight: 600, flexShrink: 0,
                  }}>
                    {item.category}
                  </span>
                  <span style={{
                    fontSize: 13, fontWeight: 600, color: "#111",
                    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1, minWidth: 0,
                  }}>
                    {item.product_name}
                  </span>
                  {analysis && <ScoreBadge score={analysis.best_score} />}
                  {analysis?.needs_review && (
                    <span style={{
                      fontSize: 10, fontWeight: 700,
                      background: "#fff7ed", color: "#c2410c",
                      border: "1px solid #fed7aa",
                      padding: "1px 6px", borderRadius: 99,
                    }}>
                      검토 필요
                    </span>
                  )}
                </div>

                {/* Issue tags */}
                {analysis && analysis.best_score < 1 && (
                  <IssueTags issues={
                    (analysis.candidates[0]?.issues ?? []).filter((iss) => iss !== "download_failed")
                  } />
                )}

                {/* Keywords */}
                {item.keywords?.length > 0 && (
                  <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: 5 }}>
                    {item.keywords.slice(0, 4).map((kw, j) => (
                      <span key={j} style={{
                        fontSize: 11, color: "#6b7280", background: "#f3f4f6",
                        padding: "1px 6px", borderRadius: 4,
                      }}>
                        #{kw}
                      </span>
                    ))}
                  </div>
                )}

                {/* Explanation from AI */}
                {analysis?.candidates[0]?.explanation && (
                  <div style={{
                    marginTop: 5, fontSize: 11, color: "#6b7280",
                    fontStyle: "italic", lineHeight: 1.4,
                  }}>
                    {analysis.candidates[0].explanation}
                  </div>
                )}

                <div style={{ fontSize: 11, color: "#9ca3af", marginTop: 4 }}>
                  출처: {item.source_title || item.source_url}
                </div>
              </div>

              {/* Right-side actions */}
              <div style={{ display: "flex", flexDirection: "column", gap: 6, flexShrink: 0, alignItems: "flex-end" }}>
                {item.link_url && (
                  <a href={item.link_url} target="_blank" rel="noopener noreferrer"
                    style={{
                      padding: "5px 10px", background: "#ede9fe", color: "#7c3aed",
                      borderRadius: 8, fontSize: 11, fontWeight: 600,
                      textDecoration: "none", whiteSpace: "nowrap",
                    }}>
                    구매 링크
                  </a>
                )}
                {onUpdateItem && allCandidates.length > 0 && (
                  <button
                    onClick={() => setOpenPickerIdx(isPickerOpen ? null : i)}
                    disabled={isLoading}
                    style={{
                      padding: "5px 10px",
                      background: isPickerOpen ? "#d1fae5" : "#f3f4f6",
                      color: isPickerOpen ? "#065f46" : "#374151",
                      border: `1px solid ${isPickerOpen ? "#a7f3d0" : "#d1d5db"}`,
                      borderRadius: 8, fontSize: 11, fontWeight: 600,
                      cursor: isLoading ? "not-allowed" : "pointer", whiteSpace: "nowrap",
                    }}
                  >
                    {isPickerOpen ? "닫기" : `이미지 선택 (${allCandidates.length})`}
                  </button>
                )}
              </div>
            </div>

            {/* ── Image picker tray ────────────────────────────────────── */}
            {isPickerOpen && onUpdateItem && (
              <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid #f3f4f6" }}>

                {/* Header */}
                <div style={{ fontSize: 11, color: "#6b7280", fontWeight: 700,
                              marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  후보 이미지 선택
                  {analysis && (
                    <span style={{ fontSize: 10, fontWeight: 400, marginLeft: 6, color: "#9ca3af" }}>
                      — AI 분석 결과 반영됨
                    </span>
                  )}
                </div>

                {/* Candidate thumbnails */}
                <div style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 6 }}>
                  {/* Sort candidates: if analysis exists, sort by score */}
                  {(analysis
                    ? [...allCandidates].sort((a, b) => {
                        const sa = scoreMap[a]?.score ?? 0;
                        const sb = scoreMap[b]?.score ?? 0;
                        return sb - sa;
                      })
                    : allCandidates
                  ).map((url, ci) => {
                    const isCurrent    = url === item.image_urls?.[0];
                    const isBest       = url === analysis?.best_url;
                    const candidate    = scoreMap[url];
                    const wmRegions    = candidate?.watermark_regions ?? [];
                    const hasWm        = wmRegions.length > 0;
                    const wmKey        = `${i}_${url}`;
                    const isWmLoading  = wmLoadingKey === wmKey;

                    return (
                      <div key={ci} style={{ flexShrink: 0, display: "flex", flexDirection: "column", gap: 4 }}>
                        <div
                          onClick={() => handleSelectImage(i, url)}
                          style={{
                            position: "relative", cursor: "pointer",
                            borderRadius: 8,
                            border: isCurrent
                              ? "2px solid #6366f1"
                              : isBest
                              ? "2px solid #10b981"
                              : "2px solid transparent",
                            outline: isCurrent || isBest ? "none" : "1px solid #e5e7eb",
                            overflow: "hidden",
                            transition: "border-color 0.15s",
                          }}
                          title={
                            isBest ? "AI 추천 이미지" :
                            isCurrent ? "현재 선택됨" :
                            "이 이미지 사용"
                          }
                          onMouseEnter={(e) => {
                            if (!isCurrent && !isBest)
                              (e.currentTarget as HTMLDivElement).style.borderColor = "#a5b4fc";
                          }}
                          onMouseLeave={(e) => {
                            if (!isCurrent && !isBest)
                              (e.currentTarget as HTMLDivElement).style.borderColor = "transparent";
                          }}
                        >
                          <img
                            src={proxyImageUrl(url)}
                            alt={`후보 ${ci + 1}`}
                            style={{ width: 90, height: 90, objectFit: "cover", display: "block" }}
                            onError={(e) => {
                              (e.target as HTMLImageElement).parentElement!.style.display = "none";
                            }}
                          />

                          {/* Score overlay (top-right) */}
                          {candidate && (
                            <div style={{
                              position: "absolute", top: 3, right: 3,
                              background: candidate.score >= 0.8 ? "rgba(6,95,70,0.85)"
                                        : candidate.score >= 0.65 ? "rgba(120,53,15,0.85)"
                                        : "rgba(185,28,28,0.85)",
                              color: "#fff", fontSize: 9, fontWeight: 700,
                              padding: "1px 5px", borderRadius: 99,
                            }}>
                              {Math.round(candidate.score * 100)}%
                            </div>
                          )}

                          {/* AI best badge (bottom-left) */}
                          {isBest && !isCurrent && (
                            <div style={{
                              position: "absolute", bottom: 0, left: 0, right: 0,
                              background: "rgba(16,185,129,0.9)",
                              color: "#fff", fontSize: 9, fontWeight: 700,
                              textAlign: "center", padding: "2px 0",
                            }}>
                              AI 추천
                            </div>
                          )}

                          {/* Current badge */}
                          {isCurrent && (
                            <div style={{
                              position: "absolute", bottom: 0, left: 0, right: 0,
                              background: "rgba(99,102,241,0.9)",
                              color: "#fff", fontSize: 9, fontWeight: 700,
                              textAlign: "center", padding: "2px 0",
                            }}>
                              현재
                            </div>
                          )}

                          {/* Watermark count badge */}
                          {hasWm && (
                            <div style={{
                              position: "absolute", top: 3, left: 3,
                              background: "rgba(180,83,9,0.9)",
                              color: "#fff", fontSize: 9, fontWeight: 700,
                              padding: "1px 5px", borderRadius: 99,
                              zIndex: 3,
                            }}>
                              WM{wmRegions.length > 1 ? ` ×${wmRegions.length}` : ""}
                            </div>
                          )}

                          {/* Watermark rectangles — one per detected region */}
                          {wmRegions.map((r, ri) => (
                            <div
                              key={ri}
                              style={{
                                position: "absolute",
                                left:   `${r.x * 100}%`,
                                top:    `${r.y * 100}%`,
                                width:  `${r.w * 100}%`,
                                height: `${r.h * 100}%`,
                                border: "2px solid #ef4444",
                                boxSizing: "border-box",
                                pointerEvents: "none",
                                zIndex: 2,
                              }}
                              title={r.description || `워터마크 ${ri + 1}`}
                            />
                          ))}
                        </div>

                        {/* Issue tags for this candidate */}
                        {candidate?.issues?.length > 0 && (
                          <div style={{ display: "flex", gap: 2, flexWrap: "wrap", maxWidth: 90 }}>
                            {candidate.issues.slice(0, 2).map((iss) => {
                              const meta = ISSUE_META[iss];
                              return meta ? (
                                <span key={iss} style={{
                                  fontSize: 8, fontWeight: 600,
                                  background: meta.bg, color: meta.color,
                                  padding: "0 4px", borderRadius: 99,
                                }}>
                                  {meta.label}
                                </span>
                              ) : null;
                            })}
                          </div>
                        )}

                        {/* WM 제거 버튼 (워터마크 있을 때만) */}
                        {hasWm && onRemoveWatermark && (
                          <button
                            onClick={() => handleRemoveWatermark(i, url, wmRegions)}
                            disabled={isWmLoading}
                            style={{
                              padding: "3px 6px", fontSize: 9, fontWeight: 600,
                              background: isWmLoading ? "#f3f4f6" : "#fff7ed",
                              color: isWmLoading ? "#9ca3af" : "#c2410c",
                              border: "1px solid #fed7aa",
                              borderRadius: 6, cursor: isWmLoading ? "not-allowed" : "pointer",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {isWmLoading ? "처리 중..." : "WM 제거"}
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* ── 유사 이미지 검색 버튼 + 결과 ────────────────── */}
                <div style={{ marginTop: 10, paddingTop: 10, borderTop: "1px solid #f3f4f6" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                    <button
                      onClick={() => {
                        const bestWmRegions = analysis?.candidates[0]?.watermark_regions ?? [];
                        // Use original image URL (not processed path) for similarity search
                        const searchUrl = item.image_urls?.[0] || currentUrl;
                        handleSimilarSearch(i, item, searchUrl, bestWmRegions);
                      }}
                      disabled={simState.loading}
                      style={{
                        padding: "5px 12px", fontSize: 11, fontWeight: 600,
                        background: simState.loading ? "#f3f4f6" : "#ecfdf5",
                        color: simState.loading ? "#9ca3af" : "#065f46",
                        border: `1px solid ${simState.loading ? "#d1d5db" : "#a7f3d0"}`,
                        borderRadius: 8, cursor: simState.loading ? "not-allowed" : "pointer",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {simState.loading ? "블로그 검색 중..." : "유사 이미지 검색"}
                    </button>
                    {simState.result && (
                      <span style={{ fontSize: 10, color: "#6b7280" }}>
                        {simState.result.processed_path
                          ? `원본 합성 완료 (${simState.result.method})`
                          : simState.result.similar_urls.length > 0
                          ? `유사 이미지 ${simState.result.similar_urls.length}장 — 직접 선택`
                          : "유사 이미지 없음"}
                        {simState.result.new_sources.length > 0 && (
                          <span style={{ marginLeft: 6, color: "#7c3aed" }}>
                            +{simState.result.new_sources.length} 소스 등록
                          </span>
                        )}
                      </span>
                    )}
                  </div>

                  {/* 유사 이미지 결과 썸네일 */}
                  {simState.result && simState.result.similar_urls.length > 0 && (
                    <div style={{ display: "flex", gap: 6, overflowX: "auto", paddingBottom: 4 }}>
                      {simState.result.similar_urls.map((rUrl, ri) => (
                        <div
                          key={ri}
                          onClick={() => handleSelectImage(i, rUrl)}
                          style={{
                            flexShrink: 0, cursor: "pointer",
                            borderRadius: 6, overflow: "hidden",
                            border: "2px solid transparent",
                            outline: "1px solid #a7f3d0",
                            transition: "border-color 0.15s",
                          }}
                          onMouseEnter={(e) => {
                            (e.currentTarget as HTMLDivElement).style.borderColor = "#10b981";
                          }}
                          onMouseLeave={(e) => {
                            (e.currentTarget as HTMLDivElement).style.borderColor = "transparent";
                          }}
                          title={`유사 이미지 ${ri + 1} — 클릭하여 사용`}
                        >
                          <img
                            src={proxyImageUrl(rUrl)}
                            alt={`유사 ${ri + 1}`}
                            style={{ width: 80, height: 80, objectFit: "cover", display: "block" }}
                            onError={(e) => {
                              (e.target as HTMLImageElement).parentElement!.style.display = "none";
                            }}
                          />
                        </div>
                      ))}
                    </div>
                  )}
                  {simState.result && simState.result.similar_urls.length === 0 && (
                    <div style={{ fontSize: 11, color: "#9ca3af", fontStyle: "italic" }}>
                      유사 이미지를 찾지 못했습니다.
                    </div>
                  )}
                </div>

                {/* Custom URL input */}
                <div style={{ marginTop: 10, display: "flex", gap: 6, alignItems: "center" }}>
                  <input
                    type="url"
                    placeholder="직접 이미지 URL 입력..."
                    value={customUrls[i] ?? ""}
                    onChange={(e) => setCustomUrls((prev) => ({ ...prev, [i]: e.target.value }))}
                    onKeyDown={(e) => { if (e.key === "Enter") handleCustomUrl(i); }}
                    style={{
                      flex: 1, padding: "6px 10px", fontSize: 12,
                      border: "1px solid #d1d5db", borderRadius: 8,
                      outline: "none",
                    }}
                  />
                  <button
                    onClick={() => handleCustomUrl(i)}
                    disabled={!customUrls[i]?.trim() || isLoading}
                    style={{
                      padding: "6px 12px", fontSize: 12, fontWeight: 600,
                      background: customUrls[i]?.trim() ? "#ede9fe" : "#f3f4f6",
                      color: customUrls[i]?.trim() ? "#7c3aed" : "#9ca3af",
                      border: "none", borderRadius: 8,
                      cursor: customUrls[i]?.trim() ? "pointer" : "not-allowed",
                      whiteSpace: "nowrap",
                    }}
                  >
                    적용
                  </button>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
    </>
  );
}
