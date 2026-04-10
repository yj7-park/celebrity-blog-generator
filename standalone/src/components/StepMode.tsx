import { useState } from "react";
import { createClient, getTrendingCelebs } from "../lib/analyzer";
import { collectPosts, scrapePostsForCeleb, type PostItem } from "../lib/collector";
import { generateBlogPost } from "../lib/generator";
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
  items: Record<string, string>;
  snippets: string[];
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
  items: {}, snippets: [], blogPost: "",
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

  // ── Step 1: Collect ────────────────────────────────────────────
  const runCollect = async () => {
    if (!apiKey.trim()) { setStep("collect", { status: "error", error: "OpenAI API 키를 입력해주세요." }); return; }
    setStep("collect", { status: "running", progress: { step: "RSS 수집 시작...", percent: 0 }, error: undefined });
    setData(INITIAL_DATA);
    setSteps(prev => ({ ...prev, analyze: INITIAL_STEPS.analyze, items: INITIAL_STEPS.items, generate: INITIAL_STEPS.generate }));

    try {
      const posts = await collectPosts(days, (done, total) =>
        setProgress("collect", `RSS 수집 중... (${done}/${total})`, Math.round((done / total) * 100))
      );
      if (!posts.length) {
        setStep("collect", { status: "error", error: "최근 게시글을 찾을 수 없습니다." }); return;
      }
      setData(prev => ({ ...prev, posts }));
      setStep("collect", { status: "done", progress: { step: "완료!", percent: 100 } });
    } catch (e) {
      setStep("collect", { status: "error", error: String(e) });
    }
  };

  // ── Step 2: Analyze ────────────────────────────────────────────
  const runAnalyze = async () => {
    setStep("analyze", { status: "running", progress: { step: "연예인 분석 시작...", percent: 0 }, error: undefined });
    setSteps(prev => ({ ...prev, items: INITIAL_STEPS.items, generate: INITIAL_STEPS.generate }));

    try {
      const client = createClient(apiKey.trim());
      const trending = await getTrendingCelebs(data.posts, client, 3, (done, total) =>
        setProgress("analyze", `분석 중... (${done}/${total})`, Math.round((done / total) * 100))
      );
      if (!trending.length) {
        setStep("analyze", { status: "error", error: "연예인을 찾을 수 없습니다." }); return;
      }
      setData(prev => ({ ...prev, trending, selectedCeleb: trending[0] }));
      setStep("analyze", { status: "done", progress: { step: "완료!", percent: 100 } });
    } catch (e) {
      setStep("analyze", { status: "error", error: String(e) });
    }
  };

  // ── Step 3: Items ──────────────────────────────────────────────
  const runItems = async () => {
    const celeb = data.selectedCeleb;
    setStep("items", { status: "running", progress: { step: `${celeb} 아이템 수집...`, percent: 0 }, error: undefined });
    setSteps(prev => ({ ...prev, generate: INITIAL_STEPS.generate }));

    try {
      const { items, snippets } = await scrapePostsForCeleb(data.posts, celeb, 5, (done, total) =>
        setProgress("items", `스크랩 중... (${done}/${total})`, Math.round((done / total) * 100))
      );
      setData(prev => ({ ...prev, items, snippets }));
      setStep("items", { status: "done", progress: { step: "완료!", percent: 100 } });
    } catch (e) {
      setStep("items", { status: "error", error: String(e) });
    }
  };

  // ── Step 4: Generate ───────────────────────────────────────────
  const runGenerate = async () => {
    setStep("generate", { status: "running", progress: { step: "블로그 포스트 생성 중...", percent: 50 }, error: undefined });

    try {
      const client = createClient(apiKey.trim());
      const post = await generateBlogPost(data.selectedCeleb, data.items, data.snippets, client);
      setData(prev => ({ ...prev, blogPost: post }));
      setStep("generate", { status: "done", progress: { step: "완료!", percent: 100 } });
    } catch (e) {
      setStep("generate", { status: "error", error: String(e) });
    }
  };

  const s = steps;
  const collectDone  = s.collect.status  === "done";
  const analyzeDone  = s.analyze.status  === "done";
  const itemsDone    = s.items.status    === "done";

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
                // Reset downstream steps when celeb changes
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
        index={3} title={`아이템 수집 — ${data.selectedCeleb || "연예인 미선택"}`}
        status={s.items.status}
        canRun={analyzeDone && s.items.status !== "running"}
        onRun={runItems}
        progress={s.items.progress}
        error={s.items.error}
      >
        {itemsDone && <ItemsPanel items={data.items} />}
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
