import { useRef, useState } from "react";
import { startPipeline, type PipelineEvent } from "./api/client";
import BlogPostPanel from "./components/BlogPostPanel";
import ItemsPanel from "./components/ItemsPanel";
import PostsPanel from "./components/PostsPanel";
import ProgressBar from "./components/ProgressBar";
import TrendingPanel from "./components/TrendingPanel";

interface PipelineState {
  posts: { count: number; titles: string[] } | null;
  trending: string[];
  selectedCeleb: string;
  items: Record<string, string>;
  blogPost: { celeb: string; post: string } | null;
  progress: { step: string; percent: number } | null;
  error: string | null;
  running: boolean;
}

const INITIAL: PipelineState = {
  posts: null,
  trending: [],
  selectedCeleb: "",
  items: {},
  blogPost: null,
  progress: null,
  error: null,
  running: false,
};

export default function App() {
  const [apiKey, setApiKey] = useState("");
  const [days, setDays] = useState(2);
  const [state, setState] = useState<PipelineState>(INITIAL);
  const esRef = useRef<EventSource | null>(null);

  const handleStart = () => {
    if (!apiKey.trim()) {
      setState((s) => ({ ...s, error: "OpenAI API 키를 입력해주세요." }));
      return;
    }
    if (esRef.current) esRef.current.close();

    setState({ ...INITIAL, running: true });

    esRef.current = startPipeline(
      days,
      apiKey.trim(),
      (event: PipelineEvent) => {
        setState((prev) => {
          switch (event.type) {
            case "progress":
              return { ...prev, progress: { step: event.step, percent: event.percent } };
            case "posts":
              return { ...prev, posts: event.data };
            case "trending":
              return {
                ...prev,
                trending: event.data.celebs,
                selectedCeleb: event.data.celebs[0] ?? "",
              };
            case "items":
              return { ...prev, items: event.data.items };
            case "blog_post":
              return { ...prev, blogPost: event.data, running: false };
            case "error":
              return { ...prev, error: event.message, running: false };
            case "done":
              return { ...prev, running: false };
            default:
              return prev;
          }
        });
      },
      (err) => setState((s) => ({ ...s, error: err, running: false }))
    );
  };

  const handleStop = () => {
    esRef.current?.close();
    setState((s) => ({ ...s, running: false }));
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #f5f3ff 0%, #eff6ff 100%)",
        fontFamily: "'Segoe UI', system-ui, sans-serif",
        padding: "32px 16px",
      }}
    >
      <div style={{ maxWidth: 860, margin: "0 auto" }}>
        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <h1 style={{ margin: "0 0 8px", fontSize: 28, fontWeight: 700, color: "#1e1b4b" }}>
            🌟 셀럽 아이템 블로그 생성기
          </h1>
          <p style={{ margin: 0, color: "#6b7280", fontSize: 14 }}>
            네이버 블로그에서 트렌딩 연예인 아이템을 수집하고 블로그 포스트를 자동 생성합니다.
          </p>
        </div>

        {/* Control panel */}
        <div
          style={{
            background: "#fff",
            border: "1px solid #e5e7eb",
            borderRadius: 16,
            padding: "24px 28px",
            marginBottom: 20,
            boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
          }}
        >
          <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 12, marginBottom: 16 }}>
            <input
              type="password"
              placeholder="OpenAI API Key (sk-...)"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              style={{
                padding: "10px 14px",
                border: "1px solid #d1d5db",
                borderRadius: 10,
                fontSize: 14,
                outline: "none",
                width: "100%",
                boxSizing: "border-box",
              }}
            />
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <label style={{ fontSize: 13, color: "#374151", whiteSpace: "nowrap" }}>최근</label>
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                style={{
                  padding: "10px 10px",
                  border: "1px solid #d1d5db",
                  borderRadius: 10,
                  fontSize: 14,
                  background: "#fff",
                  cursor: "pointer",
                }}
              >
                {[1, 2, 3, 5, 7].map((d) => (
                  <option key={d} value={d}>
                    {d}일
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={handleStart}
              disabled={state.running}
              style={{
                flex: 1,
                padding: "12px",
                background: state.running
                  ? "#a5b4fc"
                  : "linear-gradient(90deg, #6366f1, #8b5cf6)",
                color: "#fff",
                border: "none",
                borderRadius: 10,
                fontSize: 15,
                fontWeight: 600,
                cursor: state.running ? "not-allowed" : "pointer",
                transition: "opacity 0.2s",
              }}
            >
              {state.running ? "⏳ 실행 중..." : "🚀 데이터 수집 & 블로그 생성"}
            </button>
            {state.running && (
              <button
                onClick={handleStop}
                style={{
                  padding: "12px 20px",
                  background: "#fee2e2",
                  color: "#dc2626",
                  border: "none",
                  borderRadius: 10,
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                중단
              </button>
            )}
          </div>
        </div>

        {/* Progress */}
        {state.progress && (
          <div
            style={{
              background: "#fff",
              border: "1px solid #e5e7eb",
              borderRadius: 12,
              padding: "16px 20px",
              marginBottom: 16,
            }}
          >
            <ProgressBar percent={state.progress.percent} step={state.progress.step} />
          </div>
        )}

        {/* Error */}
        {state.error && (
          <div
            style={{
              background: "#fef2f2",
              border: "1px solid #fecaca",
              borderRadius: 10,
              padding: "12px 16px",
              color: "#dc2626",
              fontSize: 14,
              marginBottom: 16,
            }}
          >
            ⚠️ {state.error}
          </div>
        )}

        {/* Results grid */}
        {(state.posts || state.trending.length > 0) && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 8 }}>
            {state.posts && (
              <PostsPanel count={state.posts.count} titles={state.posts.titles} />
            )}
            {state.trending.length > 0 && (
              <TrendingPanel
                celebs={state.trending}
                selected={state.selectedCeleb}
                onSelect={(c) => setState((s) => ({ ...s, selectedCeleb: c }))}
              />
            )}
          </div>
        )}

        {Object.keys(state.items).length > 0 && <ItemsPanel items={state.items} />}
        {state.blogPost && (
          <BlogPostPanel celeb={state.blogPost.celeb} post={state.blogPost.post} />
        )}
      </div>
    </div>
  );
}
