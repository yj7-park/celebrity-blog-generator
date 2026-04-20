import { useState } from "react";
import { createClient, getTrendingCelebs } from "../lib/analyzer";
import { collectPosts, scrapeMultiplePosts } from "../lib/collector";
import { extractItemsFromPosts } from "../lib/extractor";
import { generateBlogPost } from "../lib/generator";
import type { CelebItem, PostItem } from "../lib/types";
import BlogPostPanel from "./BlogPostPanel";
import ItemsPanel from "./ItemsPanel";
import PostsPanel from "./PostsPanel";
import StepCard, { type StepStatus } from "./StepCard";
import TrendingPanel from "./TrendingPanel";

interface StepState {
  status: StepStatus;
  progress?: { step: string; percent: number };
  error?: string;
}

interface PipelineData {
  posts: PostItem[];
  trending: string[];
  selectedCeleb: string;
  celebItems: CelebItem[];
  blogPost: string;
}

const INITIAL_STEPS: Record<string, StepState> = {
  collect:  { status: "idle" },
  analyze:  { status: "idle" },
  items:    { status: "idle" },
  generate: { status: "idle" },
};

const INITIAL_DATA: PipelineData = {
  posts: [], trending: [], selectedCeleb: "",
  celebItems: [], blogPost: "",
};

interface Props {
  apiKey: string;
  days: number;
}

export default function StepMode({ apiKey, days }: Props) {
  const [steps, setSteps] = useState(INITIAL_STEPS);
  const [data, setData] = useState<PipelineData>(INITIAL_DATA);

  const setStep = (key: string, patch: Partial<StepState>) =>
    setSteps(prev => ({ ...prev, [key]: { ...prev[key], ...patch } }));

  const setProgress = (key: string, step: string, percent: number) =>
    setStep(key, { progress: { step, percent } });

  // ── Step 1: Collect RSS ────────────────────────────────────────
  const runCollect = async () => {
    if (!apiKey.trim()) {
      setStep("collect", { status: "error", error: "OpenAI API 키를 입력해주세요." });
      return;
    }
    setStep("collect", { status: "running", progress: { step: "RSS 수집 시작...", percent: 0 }, error: undefined });
    setData(INITIAL_DATA);
    setSteps(prev => ({
      ...prev,
      analyze: INITIAL_STEPS.analyze,
      items:   INITIAL_STEPS.items,
      generate: INITIAL_STEPS.generate,
    }));

    try {
      const posts = await collectPosts(days, (done, total) =>
        setProgress("collect", `RSS 수집 중... (${done}/${total})`, Math.round((done / total) * 100))
      );
      if (!posts.length) {
        setStep("collect", { status: "error", error: "최근 게시글을 찾을 수 없습니다." });
        return;
      }
      setData(prev => ({ ...prev, posts }));
      setStep("collect", { status: "done", progress: { step: `완료! ${posts.length}개 게시글 수집`, percent: 100 } });
    } catch (e) {
      setStep("collect", { status: "error", error: String(e) });
    }
  };

  // ── Step 2: Analyze trending celebs ───────────────────────────
  const runAnalyze = async () => {
    setStep("analyze", { status: "running", progress: { step: "연예인 분석 중...", percent: 0 }, error: undefined });
    setSteps(prev => ({ ...prev, items: INITIAL_STEPS.items, generate: INITIAL_STEPS.generate }));

    try {
      const client = createClient(apiKey.trim());
      const trending = await getTrendingCelebs(data.posts, client, 5, (done, total) =>
        setProgress("analyze", `분석 중... (${done}/${total})`, Math.round((done / total) * 100))
      );
      if (!trending.length) {
        setStep("analyze", { status: "error", error: "연예인을 찾을 수 없습니다." });
        return;
      }
      setData(prev => ({ ...prev, trending, selectedCeleb: trending[0] }));
      setStep("analyze", { status: "done", progress: { step: `완료! ${trending.length}명 분석`, percent: 100 } });
    } catch (e) {
      setStep("analyze", { status: "error", error: String(e) });
    }
  };

  // ── Step 3: Scrape + Extract CelebItems ───────────────────────
  const runItems = async () => {
    const celeb = data.selectedCeleb;
    if (!celeb) {
      setStep("items", { status: "error", error: "연예인을 선택해주세요." });
      return;
    }
    setStep("items", {
      status: "running",
      progress: { step: `${celeb} 관련 포스트 스크랩 중...`, percent: 0 },
      error: undefined,
    });
    setSteps(prev => ({ ...prev, generate: INITIAL_STEPS.generate }));

    try {
      const client = createClient(apiKey.trim());

      // Filter posts containing the celeb's name in title, fall back to all posts
      const celebPosts = data.posts.filter(p =>
        p.title.includes(celeb)
      );
      const targetPosts = celebPosts.length >= 3 ? celebPosts : data.posts;

      // Phase A: scrape HTML
      const maxPosts = Math.min(10, targetPosts.length);
      const scraped = await scrapeMultiplePosts(targetPosts, maxPosts, (done, total) =>
        setProgress("items", `HTML 스크랩 중... (${done}/${total})`, Math.round((done / total) * 50))
      );

      if (!scraped.length) {
        setStep("items", { status: "error", error: "스크랩된 포스트가 없습니다." });
        return;
      }

      setProgress("items", "LLM으로 아이템 추출 중...", 55);

      // Phase B: LLM extraction
      const allItems = await extractItemsFromPosts(scraped, client, (done, total) =>
        setProgress("items", `LLM 추출 중... (${done}/${total})`, Math.round(55 + (done / total) * 40))
      );

      // Filter to selected celeb (partial match)
      const celebItems = allItems.filter(it =>
        it.celeb.includes(celeb) || celeb.includes(it.celeb)
      );
      const finalItems = celebItems.length > 0 ? celebItems : allItems;

      setData(prev => ({ ...prev, celebItems: finalItems }));
      setStep("items", {
        status: "done",
        progress: { step: `완료! ${finalItems.length}개 아이템 추출`, percent: 100 },
      });
    } catch (e) {
      setStep("items", { status: "error", error: String(e) });
    }
  };

  // ── Step 4: Generate blog post ─────────────────────────────────
  const runGenerate = async () => {
    setStep("generate", { status: "running", progress: { step: "블로그 포스트 생성 중...", percent: 50 }, error: undefined });

    try {
      const client = createClient(apiKey.trim());
      const blogPost = await generateBlogPost(data.celebItems, client);
      setData(prev => ({ ...prev, blogPost }));
      setStep("generate", { status: "done", progress: { step: "완료!", percent: 100 } });
    } catch (e) {
      setStep("generate", { status: "error", error: String(e) });
    }
  };

  const s = steps;
  const collectDone = s.collect.status === "done";
  const analyzeDone = s.analyze.status === "done";
  const itemsDone   = s.items.status   === "done";

  return (
    <div>
      {/* Step 1 */}
      <StepCard
        index={1} title="블로그 게시글 수집"
        status={s.collect.status}
        canRun={s.collect.status !== "running"}
        onRun={runCollect}
        progress={s.collect.progress}
        error={s.collect.error}
      >
        {collectDone && data.posts.length > 0 && (
          <PostsPanel count={data.posts.length} titles={data.posts.slice(0, 8).map(p => p.title)} />
        )}
      </StepCard>

      {/* Step 2 */}
      <StepCard
        index={2} title="트렌딩 연예인 분석"
        status={s.analyze.status}
        canRun={collectDone && s.analyze.status !== "running"}
        onRun={runAnalyze}
        progress={s.analyze.progress}
        error={s.analyze.error}
      >
        {analyzeDone && data.trending.length > 0 && (
          <>
            <TrendingPanel
              celebs={data.trending}
              selected={data.selectedCeleb}
              onSelect={(c) => {
                setData(prev => ({ ...prev, selectedCeleb: c }));
                setSteps(prev => ({ ...prev, items: INITIAL_STEPS.items, generate: INITIAL_STEPS.generate }));
              }}
            />
            <p style={{ margin: "8px 0 0", fontSize: 12, color: "#6b7280" }}>
              💡 다른 연예인을 선택하면 3단계부터 재실행됩니다.
            </p>
          </>
        )}
      </StepCard>

      {/* Step 3 */}
      <StepCard
        index={3}
        title={`아이템 추출 — ${data.selectedCeleb || "연예인 미선택"}`}
        status={s.items.status}
        canRun={analyzeDone && s.items.status !== "running"}
        onRun={runItems}
        progress={s.items.progress}
        error={s.items.error}
      >
        {itemsDone && <ItemsPanel items={data.celebItems} />}
      </StepCard>

      {/* Step 4 */}
      <StepCard
        index={4} title="블로그 포스트 생성"
        status={s.generate.status}
        canRun={itemsDone && s.generate.status !== "running"}
        onRun={runGenerate}
        progress={s.generate.progress}
        error={s.generate.error}
      >
        {s.generate.status === "done" && data.blogPost && (
          <BlogPostPanel celeb={data.selectedCeleb} post={data.blogPost} />
        )}
      </StepCard>
    </div>
  );
}
