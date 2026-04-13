import { useEffect, useState } from "react";
import {
  listCelebItems, deleteCelebItem, deleteCelebItemsByPost,
  listScrapedPosts, deleteScrapedPost,
} from "../lib/api";
import type { CelebItemRecord, ScrapedPostRecord } from "../lib/types";

type Tab = "items" | "cache";

const card: React.CSSProperties = {
  background: "#fff",
  border: "1px solid rgba(99,102,241,0.1)",
  borderRadius: 18,
  padding: "24px 28px",
  boxShadow: "0 4px 20px rgba(30,27,75,0.07), 0 1px 4px rgba(30,27,75,0.04)",
};

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString("ko-KR", {
      year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

// ── Celeb Items Tab ────────────────────────────────────────────────────────────

function CelebItemsTab() {
  const [items, setItems] = useState<CelebItemRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterCeleb, setFilterCeleb] = useState("");
  const [inputCeleb, setInputCeleb] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deletingPost, setDeletingPost] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const load = async (celeb = "") => {
    setLoading(true);
    setError(null);
    try {
      const res = await listCelebItems(celeb);
      setItems(res.items);
    } catch {
      setError("데이터를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleSearch = () => {
    setFilterCeleb(inputCeleb);
    load(inputCeleb);
  };

  const handleDelete = async (item: CelebItemRecord) => {
    if (!window.confirm(`"${item.product_name}" 아이템을 삭제할까요?`)) return;
    setDeletingId(item.id);
    try {
      await deleteCelebItem(item.id);
      setItems(prev => prev.filter(i => i.id !== item.id));
    } catch {
      setError("삭제에 실패했습니다.");
    } finally {
      setDeletingId(null);
    }
  };

  const handleDeleteByPost = async (postUrl: string, postTitle: string) => {
    const count = items.filter(i => i.post_url === postUrl).length;
    if (!window.confirm(`"${postTitle || postUrl}" 포스트의 아이템 ${count}개를 모두 삭제할까요?`)) return;
    setDeletingPost(postUrl);
    try {
      await deleteCelebItemsByPost(postUrl);
      setItems(prev => prev.filter(i => i.post_url !== postUrl));
    } catch {
      setError("삭제에 실패했습니다.");
    } finally {
      setDeletingPost(null);
    }
  };

  // Group by post_url for the "포스트별 삭제" action
  const postGroups = items.reduce<Record<string, CelebItemRecord[]>>((acc, item) => {
    (acc[item.post_url] = acc[item.post_url] || []).push(item);
    return acc;
  }, {});

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Search bar */}
      <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
        <input
          value={inputCeleb}
          onChange={e => setInputCeleb(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleSearch()}
          placeholder="연예인 이름으로 검색..."
          style={{
            flex: 1, maxWidth: 280, padding: "8px 14px", fontSize: 14,
            border: "1px solid #e5e7eb", borderRadius: 8, outline: "none",
          }}
        />
        <button
          onClick={handleSearch}
          style={{
            padding: "8px 18px", fontSize: 13, fontWeight: 600,
            background: "#6366f1", color: "#fff", border: "none",
            borderRadius: 8, cursor: "pointer",
          }}
        >
          검색
        </button>
        {filterCeleb && (
          <button
            onClick={() => { setInputCeleb(""); setFilterCeleb(""); load(""); }}
            style={{
              padding: "8px 14px", fontSize: 13,
              background: "#f3f4f6", border: "none", borderRadius: 8,
              cursor: "pointer", color: "#6b7280",
            }}
          >
            전체 보기
          </button>
        )}
        <span style={{ fontSize: 13, color: "#6b7280", marginLeft: "auto" }}>
          {items.length}개 아이템
        </span>
      </div>

      {error && (
        <div style={{
          background: "#fef2f2", border: "1px solid #fecaca",
          borderRadius: 8, padding: "10px 14px", color: "#dc2626", fontSize: 13,
        }}>⚠️ {error}</div>
      )}

      {loading ? (
        <div style={{ textAlign: "center", padding: "40px 0", color: "#9ca3af", fontSize: 14 }}>
          불러오는 중...
        </div>
      ) : items.length === 0 ? (
        <div style={{ textAlign: "center", padding: "40px 0", color: "#9ca3af", fontSize: 14 }}>
          수집된 아이템이 없습니다.<br />
          <span style={{ fontSize: 12 }}>파이프라인을 실행하면 여기에 자동으로 저장됩니다.</span>
        </div>
      ) : (
        <>
          {/* Column header */}
          <div style={{
            display: "grid",
            gridTemplateColumns: "90px 90px 1fr 160px 100px 90px 70px",
            gap: 8, padding: "8px 12px",
            fontSize: 11, fontWeight: 600, color: "#9ca3af",
            textTransform: "uppercase", letterSpacing: "0.05em",
            borderBottom: "1px solid #f3f4f6",
          }}>
            <span>연예인</span>
            <span>카테고리</span>
            <span>제품명</span>
            <span>이슈 키워드</span>
            <span>이미지</span>
            <span>쿠팡</span>
            <span style={{ textAlign: "right" }}>작업</span>
          </div>

          {/* Rows */}
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {items.map(item => (
              <div key={item.id}>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "90px 90px 1fr 160px 100px 90px 70px",
                    gap: 8, padding: "10px 12px",
                    background: expandedId === item.id ? "#f5f3ff" : "#fafafa",
                    border: "1px solid #f3f4f6",
                    borderRadius: expandedId === item.id ? "10px 10px 0 0" : 10,
                    alignItems: "center",
                    cursor: "pointer",
                    transition: "background 0.1s",
                  }}
                  onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                  onMouseEnter={e => { if (expandedId !== item.id) (e.currentTarget as HTMLElement).style.background = "#f9f9ff"; }}
                  onMouseLeave={e => { if (expandedId !== item.id) (e.currentTarget as HTMLElement).style.background = "#fafafa"; }}
                >
                  <span style={{ fontSize: 13, fontWeight: 700, color: "#1e1b4b", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {item.celeb}
                  </span>
                  <span style={{ fontSize: 12, color: "#7c3aed", background: "#ede9fe", borderRadius: 5, padding: "2px 6px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {item.category || "—"}
                  </span>
                  <span style={{ fontSize: 13, color: "#374151", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontWeight: 500 }}>
                    {item.product_name}
                  </span>
                  <span style={{ fontSize: 11, color: "#6b7280", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {(item.keywords || []).join(" · ") || "—"}
                  </span>
                  <span style={{ fontSize: 11 }}>
                    {item.image_url ? (
                      <a href={item.image_url} target="_blank" rel="noreferrer"
                        onClick={e => e.stopPropagation()}
                        style={{ color: "#6366f1", textDecoration: "none" }}>
                        🖼 보기
                      </a>
                    ) : <span style={{ color: "#d1d5db" }}>없음</span>}
                  </span>
                  <span style={{ fontSize: 11 }}>
                    {item.coupang_url ? (
                      <a href={item.coupang_url} target="_blank" rel="noreferrer"
                        onClick={e => e.stopPropagation()}
                        style={{ color: "#ea580c", textDecoration: "none" }}>
                        🛒 링크
                      </a>
                    ) : <span style={{ color: "#d1d5db" }}>없음</span>}
                  </span>
                  <div style={{ display: "flex", justifyContent: "flex-end" }}>
                    <button
                      onClick={e => { e.stopPropagation(); handleDelete(item); }}
                      disabled={deletingId === item.id}
                      style={{
                        padding: "4px 10px", fontSize: 11, fontWeight: 600,
                        background: "#fef2f2", color: "#dc2626",
                        border: "none", borderRadius: 6,
                        cursor: deletingId === item.id ? "not-allowed" : "pointer",
                      }}
                    >
                      삭제
                    </button>
                  </div>
                </div>

                {/* Expanded detail */}
                {expandedId === item.id && (
                  <div style={{
                    background: "#f5f3ff", border: "1px solid #e0e7ff",
                    borderTop: "none", borderRadius: "0 0 10px 10px",
                    padding: "12px 14px", fontSize: 12,
                    display: "flex", flexDirection: "column", gap: 6,
                  }}>
                    <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
                      <div>
                        <span style={{ color: "#6b7280", fontWeight: 600 }}>소스 포스트: </span>
                        <a href={item.post_url} target="_blank" rel="noreferrer"
                          style={{ color: "#6366f1" }}>
                          {item.post_title || item.post_url}
                        </a>
                      </div>
                      <div>
                        <span style={{ color: "#6b7280", fontWeight: 600 }}>수집일: </span>
                        {formatDate(item.created_at)}
                      </div>
                    </div>
                    {item.image_url && (
                      <div>
                        <img
                          src={item.image_url} alt={item.product_name}
                          style={{ maxHeight: 120, borderRadius: 6, border: "1px solid #e5e7eb" }}
                          onError={e => { (e.target as HTMLImageElement).style.display = "none"; }}
                        />
                      </div>
                    )}
                    <button
                      onClick={() => handleDeleteByPost(item.post_url, item.post_title)}
                      disabled={deletingPost === item.post_url}
                      style={{
                        alignSelf: "flex-start", padding: "4px 12px", fontSize: 11,
                        background: "#fee2e2", color: "#b91c1c",
                        border: "none", borderRadius: 6, cursor: "pointer",
                        fontWeight: 600,
                      }}
                    >
                      이 포스트 아이템 전체 삭제 ({(postGroups[item.post_url] || []).length}개)
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ── Scraped Posts Cache Tab ────────────────────────────────────────────────────

function ScrapedCacheTab() {
  const [posts, setPosts] = useState<ScrapedPostRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listScrapedPosts()
      .then(r => setPosts(r.posts))
      .catch(() => setError("캐시 목록을 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }, []);

  const handleDelete = async (post: ScrapedPostRecord) => {
    if (!window.confirm(`"${post.post_title || post.post_url}" 캐시를 삭제할까요?\n(삭제 시 다음 실행에서 재스크랩됩니다)`)) return;
    setDeletingId(post.id);
    try {
      await deleteScrapedPost(post.id);
      setPosts(prev => prev.filter(p => p.id !== post.id));
    } catch {
      setError("삭제에 실패했습니다.");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <p style={{ margin: 0, fontSize: 13, color: "#6b7280" }}>
          스크랩된 포스트 캐시입니다. 삭제하면 다음 파이프라인 실행 시 해당 포스트를 재스크랩·재추출합니다.
        </p>
        <span style={{ fontSize: 13, color: "#6b7280" }}>{posts.length}개 캐시</span>
      </div>

      {error && (
        <div style={{
          background: "#fef2f2", border: "1px solid #fecaca",
          borderRadius: 8, padding: "10px 14px", color: "#dc2626", fontSize: 13,
        }}>⚠️ {error}</div>
      )}

      {loading ? (
        <div style={{ textAlign: "center", padding: "40px 0", color: "#9ca3af", fontSize: 14 }}>
          불러오는 중...
        </div>
      ) : posts.length === 0 ? (
        <div style={{ textAlign: "center", padding: "40px 0", color: "#9ca3af", fontSize: 14 }}>
          스크랩 캐시가 없습니다.
        </div>
      ) : (
        <>
          <div style={{
            display: "grid",
            gridTemplateColumns: "1fr 130px 70px 60px",
            gap: 8, padding: "8px 12px",
            fontSize: 11, fontWeight: 600, color: "#9ca3af",
            textTransform: "uppercase", letterSpacing: "0.05em",
            borderBottom: "1px solid #f3f4f6",
          }}>
            <span>포스트</span>
            <span>스크랩 일시</span>
            <span style={{ textAlign: "center" }}>해시</span>
            <span style={{ textAlign: "right" }}>작업</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
            {posts.map(post => (
              <div key={post.id} style={{
                display: "grid",
                gridTemplateColumns: "1fr 130px 70px 60px",
                gap: 8, padding: "10px 12px",
                background: "#fafafa", border: "1px solid #f3f4f6",
                borderRadius: 8, alignItems: "center",
              }}>
                <div style={{ overflow: "hidden" }}>
                  <a href={post.post_url} target="_blank" rel="noreferrer"
                    style={{ fontSize: 13, color: "#6366f1", textDecoration: "none",
                      overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                      display: "block" }}>
                    {post.post_title || post.post_url}
                  </a>
                  <span style={{ fontSize: 11, color: "#9ca3af" }}>{post.post_url.slice(0, 60)}...</span>
                </div>
                <span style={{ fontSize: 11, color: "#6b7280" }}>{formatDate(post.scraped_at)}</span>
                <span style={{
                  fontSize: 10, color: "#9ca3af", fontFamily: "monospace",
                  background: "#f3f4f6", borderRadius: 4, padding: "2px 4px",
                  textAlign: "center",
                }}>
                  {post.content_hash.slice(0, 8)}
                </span>
                <div style={{ display: "flex", justifyContent: "flex-end" }}>
                  <button
                    onClick={() => handleDelete(post)}
                    disabled={deletingId === post.id}
                    style={{
                      padding: "4px 10px", fontSize: 11, fontWeight: 600,
                      background: "#fef2f2", color: "#dc2626",
                      border: "none", borderRadius: 6,
                      cursor: deletingId === post.id ? "not-allowed" : "pointer",
                    }}
                  >
                    삭제
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function CollectedDataPage() {
  const [tab, setTab] = useState<Tab>("items");

  const tabStyle = (active: boolean): React.CSSProperties => ({
    padding: "8px 20px",
    fontSize: 14, fontWeight: active ? 700 : 500,
    color: active ? "#6366f1" : "#6b7280",
    background: active ? "#ede9fe" : "transparent",
    border: "none", borderRadius: 8,
    cursor: "pointer",
    transition: "all 0.15s",
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={card}>
        {/* Header + tabs */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24 }}>
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: "#1e1b4b" }}>
            수집 데이터 관리
          </h2>
          <div style={{
            marginLeft: "auto", display: "flex", gap: 4,
            background: "#f3f4f6", borderRadius: 10, padding: 4,
          }}>
            <button style={tabStyle(tab === "items")} onClick={() => setTab("items")}>
              셀럽 아이템
            </button>
            <button style={tabStyle(tab === "cache")} onClick={() => setTab("cache")}>
              스크랩 캐시
            </button>
          </div>
        </div>

        {tab === "items" ? <CelebItemsTab /> : <ScrapedCacheTab />}
      </div>
    </div>
  );
}
