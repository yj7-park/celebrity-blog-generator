import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import {
  runPipelineSSE,
  checkRecentRun,
  deleteRun,
  writeNaverBlog,
  getNaverStatus,
  getSettings,
  cancelPipeline,
  cancelNaver,
} from "../lib/api";
import type {
  CelebItem,
  ItemImageAnalysis,
  NaverBlogElement,
  PostItem,
  PipelineRun,
} from "../lib/types";
import ItemsPanel from "../components/ItemsPanel";
import TrendingPanel from "../components/TrendingPanel";
import BlogPostPanel from "../components/BlogPostPanel";
import PostsPanel from "../components/PostsPanel";

// ── Types ─────────────────────────────────────────────────────────────────────

type SS = "idle" | "running" | "done" | "error";

// ── Shared styles ─────────────────────────────────────────────────────────────

const cardStyle: React.CSSProperties = {
  background: "#fff",
  border: "1px solid rgba(99,102,241,0.1)",
  borderRadius: 18,
  padding: "24px 28px",
  boxShadow: "0 4px 20px rgba(30,27,75,0.07), 0 1px 4px rgba(30,27,75,0.04)",
};

const inputStyle: React.CSSProperties = {
  padding: "10px 14px",
  border: "1.5px solid #e5e7eb",
  borderRadius: 10,
  fontSize: 14,
  outline: "none",
  width: "100%",
  boxSizing: "border-box",
  background: "#fafafa",
  color: "#1e1b4b",
  transition: "border-color 0.15s",
};

const selectStyle: React.CSSProperties = {
  ...inputStyle,
  appearance: "none" as const,
  backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E")`,
  backgroundRepeat: "no-repeat",
  backgroundPosition: "right 10px center",
  paddingRight: 36,
  cursor: "pointer",
};

// ── StepHeader (same as PipelinePage) ────────────────────────────────────────

function StepHeader({ step, title, status }: { step: number; title: string; status: SS }) {
  const meta: Record<SS, { color: string; label: string; bg: string; badgeBg: string }> = {
    idle:    { color: "#9ca3af", label: "대기",    bg: "#f9fafb",   badgeBg: "#f3f4f6" },
    running: { color: "#7c3aed", label: "실행 중", bg: "#f5f3ff",   badgeBg: "#ede9fe" },
    done:    { color: "#059669", label: "완료",    bg: "#f0fdf4",   badgeBg: "#d1fae5" },
    error:   { color: "#dc2626", label: "오류",    bg: "#fef2f2",   badgeBg: "#fee2e2" },
  };
  const { color, label, badgeBg } = meta[status];
  const circleGrad: Record<SS, string> = {
    idle:    "#e5e7eb",
    running: "linear-gradient(135deg, #7c3aed, #a78bfa)",
    done:    "linear-gradient(135deg, #059669, #34d399)",
    error:   "linear-gradient(135deg, #dc2626, #f87171)",
  };
  const circleColor = status === "idle" ? "#9ca3af" : "#fff";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
      <div style={{
        width: 32, height: 32, borderRadius: "50%",
        background: circleGrad[status],
        display: "flex", alignItems: "center", justifyContent: "center",
        fontWeight: 800, fontSize: 13, color: circleColor, flexShrink: 0,
        boxShadow: status !== "idle" ? "0 2px 8px rgba(99,102,241,0.25)" : "none",
      }}>
        {status === "done" ? "✓" : step}
      </div>
      <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: "#1e1b4b", flex: 1, letterSpacing: "-0.01em" }}>
        {title}
      </h3>
      <span style={{
        fontSize: 11, color,
        background: badgeBg,
        padding: "3px 10px", borderRadius: 99, fontWeight: 700,
        border: `1px solid ${color}22`,
        letterSpacing: "0.02em",
      }}>
        {label}
      </span>
    </div>
  );
}

// ── StepMsg: inline progress message ─────────────────────────────────────────

function StepMsg({ msg }: { msg: string }) {
  if (!msg) return null;
  return (
    <div style={{
      fontSize: 13, color: "#6d28d9",
      background: "linear-gradient(90deg, #f5f3ff, #ede9fe)",
      border: "1px solid #ddd6fe",
      borderRadius: 8, padding: "8px 14px", marginBottom: 12,
      display: "flex", alignItems: "center", gap: 8,
    }}>
      <span style={{ animation: "spin 1.5s linear infinite", display: "inline-block" }}>⏳</span>
      {msg}
    </div>
  );
}

function formatDaysAgo(daysAgo: number): string {
  if (daysAgo === 0) return "오늘";
  if (daysAgo === 1) return "어제";
  return `${daysAgo}일 전`;
}

// ── Main component ────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const location = useLocation();

  // Settings
  const [days, setDays]           = useState(2);
  const [maxPosts, setMaxPosts]   = useState(10);
  const [topCelebs, setTopCelebs] = useState(3);
  const [celebFilter, setCelebFilter] = useState("");

  // Run state
  const [running, setRunning] = useState(false);
  const [error, setError]     = useState<string | null>(null);

  // Per-step statuses
  const [s1, setS1] = useState<SS>("idle"); // RSS
  const [s2, setS2] = useState<SS>("idle"); // 연예인 분석
  const [s3, setS3] = useState<SS>("idle"); // 스크랩+추출
  const [s4, setS4] = useState<SS>("idle"); // AI 이미지 분석
  const [s5, setS5] = useState<SS>("idle"); // 쿠팡
  const [s6, setS6] = useState<SS>("idle"); // 블로그

  // Per-step data
  const [posts, setPosts]               = useState<PostItem[]>([]);
  const [postCount, setPostCount]       = useState<number | null>(null);
  const [trending, setTrending]         = useState<string[]>([]);
  const [items, setItems]               = useState<CelebItem[]>([]);
  const [analyses, setAnalyses]         = useState<ItemImageAnalysis[]>([]);
  const [aiLog, setAiLog]               = useState<string[]>([]);   // per-item messages
  const [reviewCount, setReviewCount]   = useState<number | null>(null);
  const [linkedCount, setLinkedCount]   = useState<number | null>(null);
  const [blogPost, setBlogPost]         = useState<{ celeb: string; title: string; post: string } | null>(null);
  const [naverElements, setNaverElements] = useState<NaverBlogElement[]>([]);
  const [blogTags, setBlogTags]         = useState<string[]>([]);

  // Current step message (shown in the active step card)
  const [stepMsg, setStepMsg] = useState("");

  // Cache modal
  const [cacheModal, setCacheModal]       = useState<PipelineRun | null>(null);
  const [overwriteBanner, setOverwriteBanner] = useState<{ previousRunId: string; celeb: string } | null>(null);
  const [fromCache, setFromCache]         = useState<string | null>(null);

  // Naver publish
  const [naverLogin, setNaverLogin]       = useState<string | null>(null);
  const [publishing, setPublishing]       = useState(false);
  const [publishedUrl, setPublishedUrl]   = useState<string | null>(null);
  const [publishError, setPublishError]   = useState<string | null>(null);
  const [publishPhase, setPublishPhase]   = useState("idle");
  const [publishMessage, setPublishMessage] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const esRef = useRef<EventSource | null>(null);

  // Load Naver login status once
  useEffect(() => {
    getSettings().then(s => setNaverLogin(s.naver_id || null)).catch(() => {});
  }, []);

  // Load run from history page navigation
  useEffect(() => {
    const state = location.state as { loadedRun?: PipelineRun } | null;
    if (state?.loadedRun) {
      const run = state.loadedRun;
      loadRunIntoView(run, true);
      window.history.replaceState({}, "");
    }
  }, [location.state]);

  // ── Helpers ───────────────────────────────────────────────────────────────

  const loadRunIntoView = (run: PipelineRun, isCache = false) => {
    setItems((run.items ?? []) as CelebItem[]);
    setBlogPost({ celeb: run.celeb, title: run.title, post: run.blog_post ?? "" });
    setNaverElements(run.elements ?? []);
    setTrending([run.celeb]);
    setS1("done"); setS2("done"); setS3("done"); setS4("done"); setS5("done"); setS6("done");
    setFromCache(isCache ? run.celeb : null);
    setOverwriteBanner(null);
    setCacheModal(null);
  };

  const resetAll = () => {
    setPosts([]); setPostCount(null); setTrending([]); setItems([]);
    setAnalyses([]); setAiLog([]); setReviewCount(null); setLinkedCount(null);
    setBlogPost(null); setNaverElements([]); setBlogTags([]);
    setError(null); setFromCache(null); setStepMsg("");
    setPublishedUrl(null); setPublishError(null); setOverwriteBanner(null);
    setS1("idle"); setS2("idle"); setS3("idle"); setS4("idle"); setS5("idle"); setS6("idle");
  };

  // ── Start pipeline ─────────────────────────────────────────────────────────

  const handleStart = async () => {
    if (celebFilter.trim()) {
      try {
        const res = await checkRecentRun(celebFilter.trim());
        if (res.found && res.run) { setCacheModal(res.run); return; }
      } catch { /* ignore */ }
    }
    doRunPipeline(null);
  };

  const doRunPipeline = (previousRun: PipelineRun | null) => {
    if (esRef.current) esRef.current.close();
    resetAll();
    setRunning(true);

    esRef.current = runPipelineSSE(
      { days, max_posts: maxPosts, top_celebs: topCelebs, openai_api_key: "" },
      (event) => {
        const { type, step: stepText, percent, data, error: evtError } = event;

        if (type === "progress") {
          setStepMsg(stepText);

          // ── Activate running states ──────────────────────────────────────
          if (percent >= 5)  setS1(s => s === "idle" ? "running" : s);
          if (percent >= 18) setS2(s => s === "idle" ? "running" : s);
          if (percent >= 33) setS3(s => s === "idle" ? "running" : s);
          if (percent >= 63) setS4(s => s === "idle" ? "running" : s);
          if (percent >= 81) setS5(s => s === "idle" ? "running" : s);
          if (percent >= 90) setS6(s => s === "idle" ? "running" : s);

          // ── Step 1 done: posts ───────────────────────────────────────────
          if (data?.posts) {
            setPosts(data.posts);
            setPostCount(data.posts.length);
            setS1("done");
          }

          // ── Step 2 done: trending ────────────────────────────────────────
          if (data?.trending) {
            setTrending(data.trending);
            setS2("done");
          }

          // ── Step 3 done: first items (~61%) ──────────────────────────────
          if (data?.items && percent >= 55 && percent < 65) {
            setItems(data.items);
            setS3("done");
          }

          // ── Step 4 (AI): per-item analysis ───────────────────────────────
          if (percent >= 63 && percent < 80) {
            if (stepText) setAiLog(prev => [...prev.slice(-49), stepText]);
            if (data?.analysis) {
              const a = data.analysis as ItemImageAnalysis;
              setAnalyses(prev => {
                const i = prev.findIndex(x => x.item_index === a.item_index);
                if (i >= 0) { const n = [...prev]; n[i] = a; return n; }
                return [...prev, a];
              });
            }
          }

          // ── Step 4 done: items after AI (~79%) ───────────────────────────
          if (data?.items && percent >= 79 && percent < 82) {
            setItems(data.items);
            if (data.review_count != null) setReviewCount(data.review_count);
            setS4("done");
          }

          // ── Step 5 done: items after Coupang (~86%) ──────────────────────
          if (data?.items && percent >= 85 && percent < 90) {
            setItems(data.items);
            setLinkedCount(data.items.filter((it: CelebItem) => it.link_url).length);
            setS5("done");
          }

        } else if (type === "done") {
          setRunning(false);
          setStepMsg("");
          setS1("done"); setS2("done"); setS3("done"); setS4("done"); setS5("done"); setS6("done");
          if (data) {
            if (data.trending)          setTrending(data.trending);
            if (data.posts_count != null) setPostCount(data.posts_count);
            if (data.items)             setItems(data.items);
            if (data.elements)          setNaverElements(data.elements);
            if (data.tags)              setBlogTags(data.tags);
            if (data.blog_post)         setBlogPost({ celeb: data.celeb ?? "", title: data.title ?? "", post: data.blog_post });
            if (previousRun && data.celeb) setOverwriteBanner({ previousRunId: previousRun.id, celeb: data.celeb });
          }
        } else if (type === "error") {
          setRunning(false);
          setError(evtError || "오류 발생");
          setS1(s => s === "running" ? "error" : s);
          setS2(s => s === "running" ? "error" : s);
          setS3(s => s === "running" ? "error" : s);
          setS4(s => s === "running" ? "error" : s);
          setS5(s => s === "running" ? "error" : s);
          setS6(s => s === "running" ? "error" : s);
        }
      },
      (err) => {
        setError(err);
        setRunning(false);
        setS1(s => s === "running" ? "error" : s);
        setS2(s => s === "running" ? "error" : s);
        setS3(s => s === "running" ? "error" : s);
        setS4(s => s === "running" ? "error" : s);
        setS5(s => s === "running" ? "error" : s);
        setS6(s => s === "running" ? "error" : s);
      }
    );
  };

  const handleStop = () => {
    esRef.current?.close();
    setRunning(false);
    cancelPipeline().catch(() => {});
    setS1(s => s === "running" ? "idle" : s);
    setS2(s => s === "running" ? "idle" : s);
    setS3(s => s === "running" ? "idle" : s);
    setS4(s => s === "running" ? "idle" : s);
    setS5(s => s === "running" ? "idle" : s);
    setS6(s => s === "running" ? "idle" : s);
  };

  const handleExportJSON = () => {
    const payload = {
      exported_at: new Date().toISOString(),
      celeb: blogPost?.celeb ?? "",
      trending,
      items,
      blog_title: blogPost?.title ?? "",
      blog_post: blogPost?.post ?? "",
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href = url; a.download = `celeb-items-${new Date().toISOString().slice(0, 10)}.json`;
    a.click(); URL.revokeObjectURL(url);
  };

  const hasResults = items.length > 0 || blogPost != null;

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

      {/* ── Cache modal ─────────────────────────────────────────────────── */}
      {cacheModal && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 300,
          background: "rgba(0,0,0,0.45)",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <div style={{
            background: "#fff", borderRadius: 20, padding: "32px 36px",
            maxWidth: 460, width: "90%",
            boxShadow: "0 20px 60px rgba(0,0,0,0.2)",
          }}>
            <div style={{ fontSize: 28, marginBottom: 12 }}>💾</div>
            <h3 style={{ margin: "0 0 8px", fontSize: 17, fontWeight: 700, color: "#1e1b4b" }}>
              기존 데이터가 있습니다
            </h3>
            <p style={{ margin: "0 0 6px", fontSize: 14, color: "#374151" }}>
              <strong>{cacheModal.celeb}</strong> 관련 데이터가{" "}
              <strong>{formatDaysAgo(cacheModal.days_ago ?? 0)}</strong> 저장되어 있습니다.
            </p>
            {cacheModal.title && (
              <p style={{ margin: "0 0 4px", fontSize: 13, color: "#6b7280" }}>제목: {cacheModal.title}</p>
            )}
            <p style={{ margin: "0 0 24px", fontSize: 13, color: "#6b7280" }}>
              아이템 {cacheModal.item_count}개 저장됨
            </p>
            <div style={{ display: "flex", gap: 10 }}>
              <button onClick={() => loadRunIntoView(cacheModal, true)} style={{
                flex: 1, padding: "11px", fontSize: 14, fontWeight: 700,
                background: "linear-gradient(90deg, #6366f1, #8b5cf6)",
                color: "#fff", border: "none", borderRadius: 10, cursor: "pointer",
              }}>기존 데이터 사용</button>
              <button onClick={() => { setCacheModal(null); doRunPipeline(cacheModal); }} style={{
                flex: 1, padding: "11px", fontSize: 14, fontWeight: 600,
                background: "#f3f4f6", color: "#374151",
                border: "none", borderRadius: 10, cursor: "pointer",
              }}>다시 생성</button>
            </div>
            <button onClick={() => setCacheModal(null)} style={{
              marginTop: 10, width: "100%", padding: "8px",
              fontSize: 13, color: "#9ca3af", background: "none",
              border: "none", cursor: "pointer",
            }}>취소</button>
          </div>
        </div>
      )}

      {/* ── Settings + Run card ──────────────────────────────────────────── */}
      <div style={{ ...cardStyle, padding: 0, overflow: "hidden" }}>
        {/* Card header gradient strip */}
        <div style={{
          background: "linear-gradient(120deg, #6366f1 0%, #8b5cf6 60%, #a78bfa 100%)",
          padding: "18px 28px 16px",
          display: "flex", alignItems: "center", gap: 12,
        }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: "rgba(255,255,255,0.2)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 18, flexShrink: 0,
          }}>⚡</div>
          <div>
            <div style={{ color: "#fff", fontWeight: 800, fontSize: 16, lineHeight: 1.2 }}>
              전체 파이프라인 실행
            </div>
            <div style={{ color: "rgba(255,255,255,0.7)", fontSize: 12, marginTop: 2 }}>
              RSS 수집 → AI 분석 → 블로그 생성
            </div>
          </div>
        </div>

        <div style={{ padding: "22px 28px" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14, marginBottom: 14 }}>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#4b5563", marginBottom: 6 }}>수집 기간</label>
              <select value={days} onChange={e => setDays(Number(e.target.value))} style={selectStyle}>
                {[1,2,3,5,7].map(d => <option key={d} value={d}>{d}일</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#4b5563", marginBottom: 6 }}>최대 포스트</label>
              <select value={maxPosts} onChange={e => setMaxPosts(Number(e.target.value))} style={selectStyle}>
                {[5,10,20,30,50].map(n => <option key={n} value={n}>{n}개</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#4b5563", marginBottom: 6 }}>연예인 수</label>
              <select value={topCelebs} onChange={e => setTopCelebs(Number(e.target.value))} style={selectStyle}>
                {[1,2,3,5].map(n => <option key={n} value={n}>{n}명</option>)}
              </select>
            </div>
          </div>

          <div style={{ marginBottom: 18 }}>
            <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#4b5563", marginBottom: 6 }}>
              연예인 이름{" "}
              <span style={{ color: "#9ca3af", fontWeight: 400 }}>(선택 — 입력 시 기존 데이터 먼저 확인)</span>
            </label>
            <input
              type="text" placeholder="예: 한소희, 아이유 ..."
              value={celebFilter} onChange={e => setCelebFilter(e.target.value)}
              style={inputStyle}
            />
          </div>

          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={handleStart} disabled={running}
              style={{
                flex: 1, padding: "13px",
                background: running
                  ? "linear-gradient(90deg, #a5b4fc, #c4b5fd)"
                  : "linear-gradient(90deg, #6366f1, #8b5cf6)",
                color: "#fff", border: "none", borderRadius: 11,
                fontSize: 15, fontWeight: 700,
                cursor: running ? "not-allowed" : "pointer",
                boxShadow: running ? "none" : "0 4px 14px rgba(99,102,241,0.4)",
                letterSpacing: "-0.01em",
              }}
            >
              {running ? "⏳ 실행 중..." : "▶ 전체 파이프라인 실행"}
            </button>
            {running && (
              <button onClick={handleStop} style={{
                padding: "13px 20px", background: "#fff0f0", color: "#dc2626",
                border: "1.5px solid #fecaca", borderRadius: 11,
                fontSize: 14, fontWeight: 700, cursor: "pointer",
              }}>⏹ 중단</button>
            )}
            {hasResults && !running && (
              <button onClick={handleExportJSON} style={{
                padding: "13px 20px", background: "#f0fdf4", color: "#16a34a",
                border: "1.5px solid #bbf7d0", borderRadius: 11,
                fontSize: 14, fontWeight: 600, cursor: "pointer", whiteSpace: "nowrap",
              }}>↓ JSON</button>
            )}
          </div>
        </div>
      </div>

      {/* ── Error ──────────────────────────────────────────────────────────── */}
      {error && (
        <div style={{
          background: "#fef2f2", border: "1px solid #fecaca",
          borderRadius: 10, padding: "12px 16px", color: "#dc2626", fontSize: 14,
        }}>⚠️ {error}</div>
      )}

      {/* ── Cache source banner ─────────────────────────────────────────────── */}
      {fromCache && (
        <div style={{
          background: "#eff6ff", border: "1px solid #bfdbfe",
          borderRadius: 10, padding: "10px 16px",
          fontSize: 13, color: "#1d4ed8",
        }}>
          📂 <strong>{fromCache}</strong> 기존 저장 데이터를 불러왔습니다.
        </div>
      )}

      {/* ── Overwrite banner ────────────────────────────────────────────────── */}
      {overwriteBanner && (
        <div style={{
          background: "#fffbeb", border: "1px solid #fde68a",
          borderRadius: 10, padding: "12px 16px",
          display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12,
        }}>
          <span style={{ fontSize: 13, color: "#92400e" }}>
            💡 <strong>{overwriteBanner.celeb}</strong>의 이전 데이터가 DB에 남아 있습니다. 새 결과로 교체하시겠습니까?
          </span>
          <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
            <button onClick={async () => {
              await deleteRun(overwriteBanner.previousRunId).catch(() => {});
              setOverwriteBanner(null);
            }} style={{
              padding: "6px 14px", fontSize: 12, fontWeight: 600,
              background: "#fef3c7", color: "#92400e",
              border: "1px solid #fde68a", borderRadius: 7, cursor: "pointer",
            }}>이전 데이터 삭제</button>
            <button onClick={() => setOverwriteBanner(null)} style={{
              padding: "6px 14px", fontSize: 12, color: "#9ca3af",
              background: "none", border: "none", cursor: "pointer",
            }}>유지</button>
          </div>
        </div>
      )}

      {/* ── Step 1: RSS 수집 ────────────────────────────────────────────────── */}
      {(s1 !== "idle" || running) && (
        <div style={{ ...cardStyle, opacity: s1 === "idle" ? 0.5 : 1 }}>
          <StepHeader step={1} title="RSS 수집" status={s1} />
          {s1 === "running" && <StepMsg msg={stepMsg} />}
          {posts.length > 0 && (
            <PostsPanel count={postCount ?? posts.length} titles={posts.slice(0, 10).map(p => p.title)} />
          )}
        </div>
      )}

      {/* ── Step 2: 연예인 분석 ─────────────────────────────────────────────── */}
      {(s2 !== "idle" || s1 === "done") && (
        <div style={{ ...cardStyle, opacity: s2 === "idle" ? 0.5 : 1 }}>
          <StepHeader step={2} title="연예인 분석" status={s2} />
          {s2 === "running" && <StepMsg msg={stepMsg} />}
          {trending.length > 0 && (
            <TrendingPanel celebs={trending} selected={trending[0]} onSelect={() => {}} />
          )}
        </div>
      )}

      {/* ── Step 3: 스크랩 + 추출 ──────────────────────────────────────────── */}
      {(s3 !== "idle" || s2 === "done") && (
        <div style={{ ...cardStyle, opacity: s3 === "idle" ? 0.5 : 1 }}>
          <StepHeader step={3} title="스크랩 + LLM 추출" status={s3} />
          {s3 === "running" && <StepMsg msg={stepMsg} />}
          {items.length > 0 && (
            <div style={{ marginTop: 4 }}>
              <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 10 }}>
                총 {items.length}개 아이템 추출됨
              </div>
              <ItemsPanel items={items} analyses={analyses} />
            </div>
          )}
        </div>
      )}

      {/* ── Step 4: AI 이미지 분석 ─────────────────────────────────────────── */}
      {(s4 !== "idle" || s3 === "done") && (
        <div style={{ ...cardStyle, opacity: s4 === "idle" ? 0.5 : 1 }}>
          <StepHeader step={4} title="AI 이미지 분석" status={s4} />

          {/* Running: progress log */}
          {s4 === "running" && (
            <div style={{
              background: "#f5f3ff", border: "1px solid #ddd6fe",
              borderRadius: 10, padding: "10px 14px", marginBottom: 12,
              maxHeight: 200, overflowY: "auto",
              display: "flex", flexDirection: "column", gap: 4,
            }}>
              {aiLog.length === 0 ? (
                <span style={{ fontSize: 13, color: "#7c3aed" }}>⏳ {stepMsg || "분석 준비 중..."}</span>
              ) : (
                aiLog.map((msg, i) => {
                  const isReview = msg.includes("⚠️");
                  const isOk     = msg.includes("✅");
                  return (
                    <div key={i} style={{
                      fontSize: 12, fontFamily: "monospace",
                      color: isReview ? "#c2410c" : isOk ? "#065f46" : "#4b5563",
                    }}>
                      {isReview ? "⚠️" : isOk ? "✅" : "⏳"} {msg.replace(/⚠️|✅/g, "").trim()}
                    </div>
                  );
                })
              )}
            </div>
          )}

          {/* Done: summary */}
          {s4 === "done" && reviewCount != null && (
            <div style={{
              fontSize: 13,
              background: reviewCount > 0 ? "#fff7ed" : "#d1fae5",
              color: reviewCount > 0 ? "#c2410c" : "#065f46",
              border: `1px solid ${reviewCount > 0 ? "#fed7aa" : "#a7f3d0"}`,
              borderRadius: 8, padding: "8px 14px", marginBottom: 12,
            }}>
              {reviewCount > 0
                ? `⚠️ ${(analyses.length || items.length)}개 중 ${reviewCount}개 검토 필요`
                : `✅ ${analyses.length || items.length}개 아이템 모두 양호 — AI 추천 이미지 적용됨`}
            </div>
          )}

          {/* Analysis results table */}
          {analyses.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {analyses.map((a, i) => {
                const item = items[a.item_index];
                const pct  = Math.round(a.best_score * 100);
                const [scoreBg, scoreColor] =
                  a.best_score >= 0.8 ? ["#d1fae5", "#065f46"] :
                  a.best_score >= 0.65 ? ["#fef3c7", "#92400e"] :
                  ["#fee2e2", "#dc2626"];
                return (
                  <div key={i} style={{
                    display: "flex", alignItems: "center", gap: 10,
                    padding: "8px 12px", borderRadius: 8,
                    background: a.needs_review ? "#fff7ed" : "#f9fafb",
                    border: `1px solid ${a.needs_review ? "#fed7aa" : "#e5e7eb"}`,
                    fontSize: 13,
                  }}>
                    <span style={{ color: a.needs_review ? "#c2410c" : "#10b981", fontSize: 15 }}>
                      {a.needs_review ? "⚠️" : "✅"}
                    </span>
                    <span style={{ flex: 1, color: "#1e1b4b", fontWeight: 500 }}>
                      {item?.product_name ?? `아이템 ${a.item_index + 1}`}
                    </span>
                    <span style={{
                      padding: "2px 8px", borderRadius: 99,
                      background: scoreBg, color: scoreColor,
                      fontWeight: 700, fontSize: 12,
                    }}>
                      {pct}%
                    </span>
                    {a.candidates[0]?.issues?.map(issue => (
                      <span key={issue} style={{
                        padding: "2px 7px", borderRadius: 99,
                        background: "#f3f4f6", color: "#6b7280", fontSize: 11,
                      }}>
                        {issue === "watermark" ? "워터마크" :
                         issue === "mismatch" ? "불일치" :
                         issue === "low_quality" ? "저품질" :
                         issue === "cropped" ? "잘림" : issue}
                      </span>
                    ))}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ── Step 5: 쿠팡 연동 ─────────────────────────────────────────────── */}
      {(s5 !== "idle" || s4 === "done") && (
        <div style={{ ...cardStyle, opacity: s5 === "idle" ? 0.5 : 1 }}>
          <StepHeader step={5} title="쿠팡 파트너스 연동" status={s5} />
          {s5 === "running" && <StepMsg msg={stepMsg} />}
          {s5 === "done" && linkedCount != null && (
            <div style={{
              fontSize: 13, color: "#065f46", background: "#d1fae5",
              border: "1px solid #a7f3d0", borderRadius: 8, padding: "8px 14px",
            }}>
              ✅ 쿠팡 어필리에이트 링크 {linkedCount}개 생성 완료
            </div>
          )}
        </div>
      )}

      {/* ── Step 6: 블로그 생성 ────────────────────────────────────────────── */}
      {(s6 !== "idle" || s5 === "done") && (
        <div style={{ ...cardStyle, opacity: s6 === "idle" ? 0.5 : 1 }}>
          <StepHeader step={6} title="블로그 포스트 생성" status={s6} />
          {s6 === "running" && <StepMsg msg={stepMsg} />}

          {blogPost && (
            <>
              {blogPost.title && (
                <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 12 }}>
                  제목: <strong style={{ color: "#1e1b4b" }}>{blogPost.title}</strong>
                </div>
              )}
              <BlogPostPanel celeb={blogPost.celeb} post={blogPost.post} />

              {/* ── 네이버 블로그 발행 ─────────────────────────────────── */}
              <div style={{ marginTop: 20, borderTop: "1px solid #f3f4f6", paddingTop: 20 }}>
                <h4 style={{ margin: "0 0 12px", fontSize: 14, fontWeight: 700, color: "#1e1b4b" }}>
                  네이버 블로그 발행
                </h4>

                <div style={{
                  display: "flex", alignItems: "center", gap: 8,
                  padding: "8px 12px", borderRadius: 8, marginBottom: 12,
                  background: naverLogin ? "#d1fae5" : "#fef3c7",
                  fontSize: 12, fontWeight: 500,
                  color: naverLogin ? "#065f46" : "#92400e",
                }}>
                  {naverLogin ? `✅ ${naverLogin} 계정으로 발행` : "⚠️ 설정에서 네이버 계정을 먼저 입력하세요."}
                </div>

                {naverElements.length > 0 && (
                  <div style={{
                    fontSize: 11, color: "#6b7280", marginBottom: 12,
                    background: "#f9fafb", borderRadius: 6, padding: "6px 10px",
                  }}>
                    {naverElements.map((el, i) => (
                      <span key={i} style={{
                        display: "inline-block", margin: "2px 3px",
                        padding: "1px 6px", borderRadius: 4,
                        background: el.type === "image" ? "#dbeafe" : el.type === "header" ? "#ede9fe" : el.type === "url_text" ? "#fef3c7" : "#f3f4f6",
                        color: el.type === "image" ? "#1d4ed8" : el.type === "header" ? "#7c3aed" : el.type === "url_text" ? "#92400e" : "#374151",
                        fontFamily: "monospace",
                      }}>{el.type}</span>
                    ))}
                    <span style={{ marginLeft: 6 }}>총 {naverElements.length}개 elements</span>
                  </div>
                )}

                {publishing && publishMessage && (
                  <div style={{
                    borderRadius: 8, padding: "10px 14px", marginBottom: 12,
                    background: publishPhase === "verification_needed" ? "#fffbeb" : "#eff6ff",
                    border: `1px solid ${publishPhase === "verification_needed" ? "#fde68a" : "#bfdbfe"}`,
                    color: publishPhase === "verification_needed" ? "#92400e" : "#1d4ed8",
                    fontSize: 13, fontWeight: 500,
                  }}>
                    {publishPhase === "verification_needed" ? "🔐 " : "⏳ "}{publishMessage}
                  </div>
                )}

                {publishError && (
                  <div style={{
                    background: "#fef2f2", border: "1px solid #fecaca",
                    borderRadius: 8, padding: "8px 12px",
                    color: "#dc2626", fontSize: 13, marginBottom: 12,
                  }}>⚠️ {publishError}</div>
                )}

                {publishedUrl && (
                  <div style={{
                    background: "#d1fae5", border: "1px solid #a7f3d0",
                    borderRadius: 8, padding: "10px 14px", marginBottom: 12,
                  }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "#065f46", marginBottom: 4 }}>✅ 발행 완료!</div>
                    <a href={publishedUrl} target="_blank" rel="noreferrer"
                      style={{ fontSize: 12, color: "#6366f1", wordBreak: "break-all" }}>
                      {publishedUrl}
                    </a>
                  </div>
                )}

                <div style={{ display: "flex", gap: 10 }}>
                  <button
                    disabled={publishing || !naverLogin || naverElements.length === 0}
                    onClick={async () => {
                      if (!blogPost || naverElements.length === 0) return;
                      setPublishing(true); setPublishError(null); setPublishedUrl(null);
                      setPublishPhase("logging_in"); setPublishMessage("Naver 로그인 중...");

                      if (pollRef.current) clearInterval(pollRef.current);
                      pollRef.current = setInterval(async () => {
                        try {
                          const s = await getNaverStatus();
                          setPublishPhase(s.phase); setPublishMessage(s.message);
                        } catch { /* ignore */ }
                      }, 3000);

                      try {
                        const res = await writeNaverBlog(blogPost.title, naverElements, blogTags);
                        if (res.blog_url) setPublishedUrl(res.blog_url);
                        else if (res.error) setPublishError(res.error);
                        else setPublishError("발행은 요청됐지만 URL을 받지 못했습니다.");
                      } catch (e) {
                        setPublishError(String(e));
                      } finally {
                        if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
                        setPublishing(false); setPublishPhase("idle"); setPublishMessage("");
                      }
                    }}
                    style={{
                      padding: "11px 24px", fontSize: 14, fontWeight: 700,
                      background: (publishing || !naverLogin || naverElements.length === 0)
                        ? "#a5b4fc"
                        : "linear-gradient(90deg, #6366f1, #8b5cf6)",
                      color: "#fff", border: "none", borderRadius: 10,
                      cursor: (publishing || !naverLogin || naverElements.length === 0) ? "not-allowed" : "pointer",
                    }}
                  >
                    {publishing
                      ? publishPhase === "verification_needed" ? "🔐 인증 대기 중..." : "⏳ 발행 중..."
                      : "네이버 블로그에 발행"}
                  </button>
                  {publishing && (
                    <button onClick={() => {
                      cancelNaver().catch(() => {});
                      setPublishing(false); setPublishPhase("idle"); setPublishMessage("");
                    }} style={{
                      padding: "11px 18px", fontSize: 13, fontWeight: 600,
                      background: "#fee2e2", color: "#dc2626",
                      border: "none", borderRadius: 10, cursor: "pointer",
                    }}>발행 중단</button>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
