import { useRef, useState } from "react";
import { runPipelineSSE } from "../lib/api";
import type { PipelineEvent, CelebItem } from "../lib/types";
import ProgressBar from "../components/ProgressBar";

type StepStatus = "idle" | "running" | "done" | "error";

interface PipelineResult {
  postCount: number;
  celebs: string[];
  itemCount: number;
  blogPost: { celeb: string; post: string } | null;
}

const STEP_LABELS = ["RSS 수집", "연예인 분석", "스크랩+추출", "블로그 생성"];

const inputStyle: React.CSSProperties = {
  padding: "10px 14px",
  border: "1px solid #d1d5db",
  borderRadius: 10,
  fontSize: 14,
  outline: "none",
  width: "100%",
  boxSizing: "border-box",
};

const cardStyle: React.CSSProperties = {
  background: "#fff",
  border: "1px solid #e5e7eb",
  borderRadius: 16,
  padding: "24px 28px",
  boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
};

export default function DashboardPage() {
  const [apiKey, setApiKey] = useState(() => sessionStorage.getItem("dash_apiKey") ?? "");
  const [days, setDays] = useState(2);
  const [maxPosts, setMaxPosts] = useState(10);
  const [topCelebs, setTopCelebs] = useState(3);

  const [stepStatus, setStepStatus] = useState<StepStatus[]>(["idle", "idle", "idle", "idle"]);
  const [currentStep, setCurrentStep] = useState(-1);
  const [progress, setProgress] = useState<{ step: string; percent: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const [result, setResult] = useState<PipelineResult | null>(() => {
    const cached = sessionStorage.getItem("dash_result");
    return cached ? JSON.parse(cached) : null;
  });

  const [copied, setCopied] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  const handleStart = () => {
    if (!apiKey.trim()) {
      setError("OpenAI API 키를 입력해주세요.");
      return;
    }
    if (esRef.current) esRef.current.close();

    sessionStorage.setItem("dash_apiKey", apiKey.trim());
    setError(null);
    setRunning(true);
    setResult(null);
    setCurrentStep(0);
    setStepStatus(["running", "idle", "idle", "idle"]);
    setProgress(null);

    let postCount = 0;
    let celebs: string[] = [];
    let itemCount = 0;

    esRef.current = runPipelineSSE(
      { days, max_posts: maxPosts, top_celebs: topCelebs, openai_api_key: apiKey.trim() },
      (event: PipelineEvent) => {
        switch (event.type) {
          case "progress": {
            setProgress({ step: event.step, percent: event.percent });
            const pct = event.percent;
            if (pct < 25) {
              setCurrentStep(0);
              setStepStatus(["running", "idle", "idle", "idle"]);
            } else if (pct < 50) {
              setCurrentStep(1);
              setStepStatus(["done", "running", "idle", "idle"]);
            } else if (pct < 75) {
              setCurrentStep(2);
              setStepStatus(["done", "done", "running", "idle"]);
            } else {
              setCurrentStep(3);
              setStepStatus(["done", "done", "done", "running"]);
            }
            break;
          }
          case "posts":
            postCount = event.data.count;
            break;
          case "trending":
            celebs = event.data.celebs;
            break;
          case "items":
            itemCount = (event.data.items as CelebItem[]).length;
            break;
          case "blog_post": {
            const newResult: PipelineResult = {
              postCount,
              celebs,
              itemCount,
              blogPost: { celeb: event.data.celeb, post: event.data.post },
            };
            setResult(newResult);
            sessionStorage.setItem("dash_result", JSON.stringify(newResult));
            setStepStatus(["done", "done", "done", "done"]);
            setRunning(false);
            setCurrentStep(-1);
            setProgress(null);
            break;
          }
          case "error":
            setError(event.message);
            setRunning(false);
            setStepStatus((prev) => prev.map((s) => (s === "running" ? "error" : s)));
            break;
          case "done":
            setRunning(false);
            setCurrentStep(-1);
            setStepStatus((prev) => prev.map((s) => (s === "running" ? "done" : s)));
            break;
        }
      },
      (err) => {
        setError(err);
        setRunning(false);
        setStepStatus((prev) => prev.map((s) => (s === "running" ? "error" : s)));
      }
    );
  };

  const handleStop = () => {
    esRef.current?.close();
    setRunning(false);
    setStepStatus((prev) => prev.map((s) => (s === "running" ? "idle" : s)));
  };

  const stepColors: Record<StepStatus, { bg: string; color: string; label: string }> = {
    idle: { bg: "#f3f4f6", color: "#9ca3af", label: "대기" },
    running: { bg: "#ede9fe", color: "#7c3aed", label: "실행 중" },
    done: { bg: "#d1fae5", color: "#065f46", label: "완료" },
    error: { bg: "#fee2e2", color: "#dc2626", label: "오류" },
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* 빠른 실행 카드 */}
      <div style={cardStyle}>
        <h2 style={{ margin: "0 0 20px", fontSize: 16, fontWeight: 700, color: "#1e1b4b" }}>
          전체 파이프라인 실행
        </h2>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginBottom: 16 }}>
          <div>
            <label style={{ display: "block", fontSize: 12, color: "#6b7280", marginBottom: 6 }}>
              수집 기간 (일)
            </label>
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              style={inputStyle}
            >
              {[1, 2, 3, 5, 7].map((d) => (
                <option key={d} value={d}>{d}일</option>
              ))}
            </select>
          </div>
          <div>
            <label style={{ display: "block", fontSize: 12, color: "#6b7280", marginBottom: 6 }}>
              최대 포스트 수
            </label>
            <select
              value={maxPosts}
              onChange={(e) => setMaxPosts(Number(e.target.value))}
              style={inputStyle}
            >
              {[5, 10, 20, 30, 50].map((n) => (
                <option key={n} value={n}>{n}개</option>
              ))}
            </select>
          </div>
          <div>
            <label style={{ display: "block", fontSize: 12, color: "#6b7280", marginBottom: 6 }}>
              분석 연예인 수
            </label>
            <select
              value={topCelebs}
              onChange={(e) => setTopCelebs(Number(e.target.value))}
              style={inputStyle}
            >
              {[1, 2, 3, 5].map((n) => (
                <option key={n} value={n}>{n}명</option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "block", fontSize: 12, color: "#6b7280", marginBottom: 6 }}>
            OpenAI API Key
          </label>
          <input
            type="password"
            placeholder="sk-..."
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            style={inputStyle}
          />
        </div>

        <div style={{ display: "flex", gap: 10 }}>
          <button
            onClick={handleStart}
            disabled={running}
            style={{
              flex: 1,
              padding: "12px",
              background: running ? "#a5b4fc" : "linear-gradient(90deg, #6366f1, #8b5cf6)",
              color: "#fff",
              border: "none",
              borderRadius: 10,
              fontSize: 15,
              fontWeight: 600,
              cursor: running ? "not-allowed" : "pointer",
            }}
          >
            {running ? "⏳ 실행 중..." : "전체 파이프라인 실행"}
          </button>
          {running && (
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

      {/* 단계 상태 */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr 1fr",
          gap: 12,
        }}
      >
        {STEP_LABELS.map((label, i) => {
          const s = stepStatus[i];
          const colors = stepColors[s];
          return (
            <div
              key={i}
              style={{
                background: colors.bg,
                borderRadius: 12,
                padding: "16px",
                textAlign: "center",
                border: currentStep === i ? "2px solid #6366f1" : "2px solid transparent",
                transition: "all 0.2s",
              }}
            >
              <div style={{ fontSize: 22, marginBottom: 6 }}>
                {s === "done" ? "✅" : s === "error" ? "❌" : s === "running" ? "⏳" : "⬜"}
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, color: "#1e1b4b", marginBottom: 4 }}>
                {i + 1}. {label}
              </div>
              <div style={{ fontSize: 11, color: colors.color, fontWeight: 500 }}>
                {colors.label}
              </div>
            </div>
          );
        })}
      </div>

      {/* 진행 바 */}
      {progress && (
        <div style={cardStyle}>
          <ProgressBar percent={progress.percent} step={progress.step} />
        </div>
      )}

      {/* 에러 */}
      {error && (
        <div
          style={{
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: 10,
            padding: "12px 16px",
            color: "#dc2626",
            fontSize: 14,
          }}
        >
          ⚠️ {error}
        </div>
      )}

      {/* 결과 요약 */}
      {result && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
            <div style={{ ...cardStyle, textAlign: "center" }}>
              <div style={{ fontSize: 32, fontWeight: 700, color: "#6366f1" }}>{result.postCount}</div>
              <div style={{ fontSize: 13, color: "#6b7280", marginTop: 4 }}>수집된 게시글</div>
            </div>
            <div style={{ ...cardStyle, textAlign: "center" }}>
              <div style={{ fontSize: 32, fontWeight: 700, color: "#8b5cf6" }}>{result.celebs.length}</div>
              <div style={{ fontSize: 13, color: "#6b7280", marginTop: 4 }}>분석된 연예인</div>
            </div>
            <div style={{ ...cardStyle, textAlign: "center" }}>
              <div style={{ fontSize: 32, fontWeight: 700, color: "#10b981" }}>{result.itemCount}</div>
              <div style={{ fontSize: 13, color: "#6b7280", marginTop: 4 }}>수집된 아이템</div>
            </div>
          </div>

          {result.celebs.length > 0 && (
            <div style={cardStyle}>
              <h3 style={{ margin: "0 0 12px", fontSize: 14, fontWeight: 600, color: "#374151" }}>
                분석된 연예인
              </h3>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {result.celebs.map((c) => (
                  <span
                    key={c}
                    style={{
                      background: "#ede9fe",
                      color: "#7c3aed",
                      padding: "4px 12px",
                      borderRadius: 99,
                      fontSize: 13,
                      fontWeight: 500,
                    }}
                  >
                    {c}
                  </span>
                ))}
              </div>
            </div>
          )}

          {result.blogPost && (
            <div style={cardStyle}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: "#374151" }}>
                  생성된 블로그 포스트 — {result.blogPost.celeb}
                </h3>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(result.blogPost!.post);
                    setCopied(true);
                    setTimeout(() => setCopied(false), 2000);
                  }}
                  style={{
                    padding: "6px 14px",
                    fontSize: 13,
                    borderRadius: 8,
                    border: "1px solid #d1d5db",
                    background: copied ? "#d1fae5" : "#fff",
                    cursor: "pointer",
                    color: copied ? "#065f46" : "#374151",
                  }}
                >
                  {copied ? "✅ 복사됨" : "📋 복사"}
                </button>
              </div>
              <pre
                style={{
                  margin: 0,
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                  fontSize: 13.5,
                  lineHeight: 1.8,
                  color: "#1f2937",
                  background: "#f9fafb",
                  padding: 16,
                  borderRadius: 8,
                  maxHeight: 500,
                  overflowY: "auto",
                }}
              >
                {result.blogPost.post}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
