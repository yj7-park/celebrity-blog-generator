import { useRef, useState } from "react";
import { createClient, getTrendingCelebs } from "./lib/analyzer";
import { collectPosts, scrapePostsForCeleb, type PostItem } from "./lib/collector";
import { generateBlogPost } from "./lib/generator";
import BlogPostPanel from "./components/BlogPostPanel";
import ItemsPanel from "./components/ItemsPanel";
import PostsPanel from "./components/PostsPanel";
import ProgressBar from "./components/ProgressBar";
import TrendingPanel from "./components/TrendingPanel";

interface Progress {
  step: string;
  percent: number;
}

interface Result {
  posts: { count: number; titles: string[] };
  trending: string[];
  selectedCeleb: string;
  items: Record<string, string>;
  blogPost: { celeb: string; post: string } | null;
}

export default function App() {
  const [apiKey, setApiKey] = useState("");
  const [days, setDays] = useState(2);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef(false);

  const setStep = (step: string, percent: number) =>
    setProgress({ step, percent });

  const handleStart = async () => {
    if (!apiKey.trim()) {
      setError("OpenAI API 키를 입력해주세요.");
      return;
    }
    abortRef.current = false;
    setRunning(true);
    setError(null);
    setResult(null);
    setProgress(null);

    try {
      const client = createClient(apiKey.trim());

      // Step 1 – collect RSS
      setStep("블로그 RSS 수집 중...", 5);
      const allPosts: PostItem[] = await collectPosts(days, (done, total) =>
        setStep(`RSS 수집 중... (${done}/${total})`, Math.round(5 + (done / total) * 20))
      );
      if (abortRef.current) return;

      if (allPosts.length === 0) {
        setError("최근 게시글을 찾을 수 없습니다.");
        return;
      }

      const postsData = {
        count: allPosts.length,
        titles: allPosts.slice(0, 10).map((p) => p.title),
      };
      setResult((prev) => ({ ...(prev ?? {} as Result), posts: postsData, trending: [], selectedCeleb: "", items: {}, blogPost: null }));

      // Step 2 – extract trending celebs
      setStep("트렌딩 연예인 분석 중...", 28);
      const trending = await getTrendingCelebs(allPosts, client, 3, (done, total) =>
        setStep(`연예인 분석 중... (${done}/${total})`, Math.round(28 + (done / total) * 30))
      );
      if (abortRef.current) return;

      if (trending.length === 0) {
        setError("연예인을 찾을 수 없습니다.");
        return;
      }

      setResult((prev) => ({
        ...(prev ?? {} as Result),
        trending,
        selectedCeleb: trending[0],
      }));

      const celeb = trending[0];

      // Step 3 – scrape items
      setStep(`${celeb} 아이템 수집 중...`, 60);
      const { items, snippets } = await scrapePostsForCeleb(
        allPosts,
        celeb,
        5,
        (done, total) =>
          setStep(`아이템 수집 중... (${done}/${total})`, Math.round(60 + (done / total) * 20))
      );
      if (abortRef.current) return;

      setResult((prev) => ({ ...(prev ?? {} as Result), items }));

      // Step 4 – generate blog post
      setStep("블로그 포스트 생성 중...", 82);
      const post = await generateBlogPost(celeb, items, snippets, client);
      if (abortRef.current) return;

      setResult((prev) => ({
        ...(prev ?? {} as Result),
        blogPost: { celeb, post },
      }));
      setStep("완료!", 100);
    } catch (e) {
      setError(String(e));
    } finally {
      setRunning(false);
    }
  };

  const handleStop = () => {
    abortRef.current = true;
    setRunning(false);
  };

  const handleCelebSelect = (c: string) =>
    setResult((prev) => prev ? { ...prev, selectedCeleb: c } : prev);

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

        {/* Controls */}
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
                  padding: "10px",
                  border: "1px solid #d1d5db",
                  borderRadius: 10,
                  fontSize: 14,
                  background: "#fff",
                  cursor: "pointer",
                }}
              >
                {[1, 2, 3, 5, 7].map((d) => (
                  <option key={d} value={d}>{d}일</option>
                ))}
              </select>
            </div>
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
              {running ? "⏳ 실행 중..." : "🚀 데이터 수집 & 블로그 생성"}
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

        {/* Progress */}
        {progress && (
          <div
            style={{
              background: "#fff",
              border: "1px solid #e5e7eb",
              borderRadius: 12,
              padding: "16px 20px",
              marginBottom: 16,
            }}
          >
            <ProgressBar percent={progress.percent} step={progress.step} />
          </div>
        )}

        {/* Error */}
        {error && (
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
            ⚠️ {error}
          </div>
        )}

        {/* Results */}
        {result && (
          <>
            {(result.posts || result.trending.length > 0) && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 8 }}>
                {result.posts && (
                  <PostsPanel count={result.posts.count} titles={result.posts.titles} />
                )}
                {result.trending.length > 0 && (
                  <TrendingPanel
                    celebs={result.trending}
                    selected={result.selectedCeleb}
                    onSelect={handleCelebSelect}
                  />
                )}
              </div>
            )}
            {Object.keys(result.items).length > 0 && <ItemsPanel items={result.items} />}
            {result.blogPost && (
              <BlogPostPanel celeb={result.blogPost.celeb} post={result.blogPost.post} />
            )}
          </>
        )}
      </div>
    </div>
  );
}
