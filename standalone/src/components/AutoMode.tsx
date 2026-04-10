import { useRef, useState } from "react";
import { createClient, getTrendingCelebs } from "../lib/analyzer";
import { collectPosts, scrapeMultiplePosts } from "../lib/collector";
import { extractItemsFromPosts } from "../lib/extractor";
import { generateBlogPost } from "../lib/generator";
import type { CelebItem, PostItem } from "../lib/types";
import BlogPostPanel from "./BlogPostPanel";
import ItemsPanel from "./ItemsPanel";
import PostsPanel from "./PostsPanel";
import ProgressBar from "./ProgressBar";
import TrendingPanel from "./TrendingPanel";

interface Result {
  posts: { count: number; titles: string[] };
  trending: string[];
  selectedCeleb: string;
  celebItems: CelebItem[];
  blogPost: { celeb: string; post: string } | null;
}

interface Props {
  apiKey: string;
  days: number;
}

export default function AutoMode({ apiKey, days }: Props) {
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<{ step: string; percent: number } | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef(false);

  const setStep = (step: string, percent: number) => setProgress({ step, percent });

  const handleStart = async () => {
    if (!apiKey.trim()) { setError("OpenAI API 키를 입력해주세요."); return; }
    abortRef.current = false;
    setRunning(true); setError(null); setResult(null); setProgress(null);

    try {
      const client = createClient(apiKey.trim());

      // ── Phase 1: RSS collect (0–20%) ──────────────────────────
      setStep("블로그 RSS 수집 중...", 5);
      const allPosts: PostItem[] = await collectPosts(days, (done, total) =>
        setStep(`RSS 수집 중... (${done}/${total})`, Math.round(5 + (done / total) * 15))
      );
      if (abortRef.current) return;
      if (!allPosts.length) { setError("최근 게시글을 찾을 수 없습니다."); return; }

      setResult({
        posts: { count: allPosts.length, titles: allPosts.slice(0, 10).map(p => p.title) },
        trending: [], selectedCeleb: "", celebItems: [], blogPost: null,
      });

      // ── Phase 2: Trending analysis (20–40%) ───────────────────
      setStep("트렌딩 연예인 분석 중...", 22);
      const trending = await getTrendingCelebs(allPosts, client, 5, (done, total) =>
        setStep(`연예인 분석 중... (${done}/${total})`, Math.round(22 + (done / total) * 18))
      );
      if (abortRef.current) return;
      if (!trending.length) { setError("연예인을 찾을 수 없습니다."); return; }

      const celeb = trending[0];
      setResult(prev => ({ ...prev!, trending, selectedCeleb: celeb }));

      // ── Phase 3a: Scrape posts (40–65%) ───────────────────────
      const celebPosts = allPosts.filter(p => p.title.includes(celeb));
      const targetPosts = celebPosts.length >= 3 ? celebPosts : allPosts;
      const maxPosts = Math.min(10, targetPosts.length);

      setStep(`${celeb} 관련 포스트 스크랩 중...`, 42);
      const scraped = await scrapeMultiplePosts(targetPosts, maxPosts, (done, total) =>
        setStep(`HTML 스크랩 중... (${done}/${total})`, Math.round(42 + (done / total) * 23))
      );
      if (abortRef.current) return;

      // ── Phase 3b: LLM extraction (65–82%) ────────────────────
      setStep("LLM으로 아이템 추출 중...", 67);
      const allItems = await extractItemsFromPosts(scraped, client, (done, total) =>
        setStep(`아이템 추출 중... (${done}/${total})`, Math.round(67 + (done / total) * 15))
      );
      if (abortRef.current) return;

      const celebItems = allItems.filter(it =>
        it.celeb.includes(celeb) || celeb.includes(it.celeb)
      );
      const finalItems = celebItems.length > 0 ? celebItems : allItems;
      setResult(prev => ({ ...prev!, celebItems: finalItems }));

      // ── Phase 4: Blog post generation (82–100%) ───────────────
      setStep("블로그 포스트 생성 중...", 84);
      const post = await generateBlogPost(finalItems, client);
      if (abortRef.current) return;

      setResult(prev => ({ ...prev!, blogPost: { celeb, post } }));
      setStep("완료!", 100);
    } catch (e) {
      setError(String(e));
    } finally {
      setRunning(false);
    }
  };

  return (
    <>
      <div style={{ display: "flex", gap: 10, marginBottom: 20 }}>
        <button
          onClick={handleStart}
          disabled={running}
          style={{
            flex: 1, padding: "12px",
            background: running ? "#a5b4fc" : "linear-gradient(90deg, #6366f1, #8b5cf6)",
            color: "#fff", border: "none", borderRadius: 10,
            fontSize: 15, fontWeight: 600, cursor: running ? "not-allowed" : "pointer",
          }}
        >
          {running ? "⏳ 실행 중..." : "🚀 데이터 수집 & 블로그 생성"}
        </button>
        {running && (
          <button
            onClick={() => { abortRef.current = true; setRunning(false); }}
            style={{
              padding: "12px 20px", background: "#fee2e2", color: "#dc2626",
              border: "none", borderRadius: 10, fontSize: 14, fontWeight: 600, cursor: "pointer",
            }}
          >
            중단
          </button>
        )}
      </div>

      {progress && (
        <div style={{
          background: "#fff", border: "1px solid #e5e7eb", borderRadius: 12,
          padding: "16px 20px", marginBottom: 16,
        }}>
          <ProgressBar percent={progress.percent} step={progress.step} />
        </div>
      )}

      {error && (
        <div style={{
          background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 10,
          padding: "12px 16px", color: "#dc2626", fontSize: 14, marginBottom: 16,
        }}>
          ⚠️ {error}
        </div>
      )}

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
                  onSelect={(c) => setResult(prev => prev ? { ...prev, selectedCeleb: c } : prev)}
                />
              )}
            </div>
          )}
          {result.celebItems.length > 0 && <ItemsPanel items={result.celebItems} />}
          {result.blogPost && (
            <BlogPostPanel celeb={result.blogPost.celeb} post={result.blogPost.post} />
          )}
        </>
      )}
    </>
  );
}
