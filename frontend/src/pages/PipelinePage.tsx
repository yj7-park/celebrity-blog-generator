import { useState, useRef } from "react";
import {
  collectPosts,
  analyzeCelebs,
  scrapePosts,
  generatePost,
  processImage,
  processImageWithWatermark,
  analyzeItemImages,
  cancelPipeline,
} from "../lib/api";
import type { PostItem, CelebItem, ItemImageAnalysis, WatermarkRegion } from "../lib/types";
import ItemsPanel from "../components/ItemsPanel";
import TrendingPanel from "../components/TrendingPanel";
import BlogPostPanel from "../components/BlogPostPanel";
import PostsPanel from "../components/PostsPanel";

type StepState = "idle" | "running" | "done" | "error";

const cardStyle: React.CSSProperties = {
  background: "#fff",
  border: "1px solid #e5e7eb",
  borderRadius: 16,
  padding: "24px 28px",
  boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
  marginBottom: 16,
};

const inputStyle: React.CSSProperties = {
  padding: "10px 14px",
  border: "1px solid #d1d5db",
  borderRadius: 10,
  fontSize: 14,
  outline: "none",
  width: "100%",
  boxSizing: "border-box",
};

function StepHeader({
  step,
  title,
  status,
}: {
  step: number;
  title: string;
  status: StepState;
}) {
  const statusMeta: Record<StepState, { color: string; label: string }> = {
    idle: { color: "#9ca3af", label: "대기" },
    running: { color: "#7c3aed", label: "실행 중" },
    done: { color: "#10b981", label: "완료" },
    error: { color: "#ef4444", label: "오류" },
  };
  const meta = statusMeta[status];
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
      <div
        style={{
          width: 32,
          height: 32,
          borderRadius: "50%",
          background: status === "idle" ? "#f3f4f6" : status === "done" ? "#d1fae5" : status === "error" ? "#fee2e2" : "#ede9fe",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontWeight: 700,
          fontSize: 14,
          color: meta.color,
          flexShrink: 0,
        }}
      >
        {step}
      </div>
      <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: "#1e1b4b", flex: 1 }}>{title}</h3>
      <span
        style={{
          fontSize: 12,
          color: meta.color,
          background: status === "idle" ? "#f3f4f6" : status === "done" ? "#d1fae5" : status === "error" ? "#fee2e2" : "#ede9fe",
          padding: "3px 10px",
          borderRadius: 99,
          fontWeight: 600,
        }}
      >
        {meta.label}
      </span>
    </div>
  );
}

function RunButton({
  onClick,
  disabled,
  loading,
  label,
}: {
  onClick: () => void;
  disabled: boolean;
  loading: boolean;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: "10px 20px",
        background: disabled ? "#a5b4fc" : "linear-gradient(90deg, #6366f1, #8b5cf6)",
        color: "#fff",
        border: "none",
        borderRadius: 10,
        fontSize: 14,
        fontWeight: 600,
        cursor: disabled ? "not-allowed" : "pointer",
      }}
    >
      {loading ? "⏳ 실행 중..." : label}
    </button>
  );
}

export default function PipelinePage() {
  const [days, setDays] = useState(2);
  const [maxPosts, setMaxPosts] = useState(10);
  const [topCelebs, setTopCelebs] = useState(3);

  // Step 1
  const [step1Status, setStep1Status] = useState<StepState>("idle");
  const [posts, setPosts] = useState<PostItem[]>([]);
  const [step1Error, setStep1Error] = useState<string | null>(null);

  // Step 2
  const [step2Status, setStep2Status] = useState<StepState>("idle");
  const [celebs, setCelebs] = useState<string[]>([]);
  const [selectedCeleb, setSelectedCeleb] = useState("");
  const [step2Error, setStep2Error] = useState<string | null>(null);

  // Step 3
  const [step3Status, setStep3Status] = useState<StepState>("idle");
  const [items, setItems] = useState<CelebItem[]>([]);
  const [step3Error, setStep3Error] = useState<string | null>(null);

  // Step 3.5 – AI 이미지 분석
  const [analyzeStatus, setAnalyzeStatus] = useState<StepState>("idle");
  const [analyzeProgress, setAnalyzeProgress] = useState<string>("");
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);
  const [analyses, setAnalyses] = useState<ItemImageAnalysis[]>([]);
  const [reviewCount, setReviewCount] = useState<number>(0);
  const analyzeControllerRef = useRef<AbortController | null>(null);

  // Step 4
  const [step4Status, setStep4Status] = useState<StepState>("idle");
  const [blogPost, setBlogPost] = useState<{ celeb: string; post: string } | null>(null);
  const [step4Error, setStep4Error] = useState<string | null>(null);
  const [imagePlacement, setImagePlacement] = useState<"두괄식" | "미괄식">("두괄식");

  // Step 1: RSS 수집
  const handleCollect = async () => {
    setStep1Status("running");
    setStep1Error(null);
    try {
      const res = await collectPosts(days);
      setPosts(res.posts);
      setStep1Status("done");
    } catch (e) {
      setStep1Error(String(e));
      setStep1Status("error");
    }
  };

  // Step 2: 연예인 분석
  const handleAnalyze = async () => {
    setStep2Status("running");
    setStep2Error(null);
    try {
      const res = await analyzeCelebs(posts, "", topCelebs);
      setCelebs(res.trending);
      setSelectedCeleb(res.trending[0] ?? "");
      setStep2Status("done");
    } catch (e) {
      setStep2Error(String(e));
      setStep2Status("error");
    }
  };

  // Step 3: 스크랩 + 추출
  const handleScrape = async () => {
    if (!selectedCeleb) { setStep3Error("연예인을 선택해주세요."); return; }
    setStep3Status("running");
    setStep3Error(null);
    try {
      const res = await scrapePosts(posts, selectedCeleb, maxPosts);
      setItems(res.items);
      setStep3Status("done");
    } catch (e) {
      setStep3Error(String(e));
      setStep3Status("error");
    }
  };

  // Image picker callback: re-process selected URL and update item
  const handleUpdateItemImage = async (index: number, newImageUrl: string) => {
    try {
      const res = await processImage(newImageUrl);
      setItems((prev) =>
        prev.map((item, i) =>
          i === index
            ? {
                ...item,
                image_urls: [newImageUrl, ...(item.image_urls ?? []).filter((u) => u !== newImageUrl)],
                processed_image_path: res.processed_path,
              }
            : item
        )
      );
    } catch {
      // silently ignore — user can try another image
    }
  };

  // Watermark removal callback
  const handleRemoveWatermark = async (index: number, url: string, region: WatermarkRegion) => {
    try {
      const res = await processImageWithWatermark(url, region);
      setItems((prev) =>
        prev.map((item, i) =>
          i === index ? { ...item, processed_image_path: res.processed_path } : item
        )
      );
    } catch {
      // silently ignore
    }
  };

  // AI image analysis
  const handleAnalyzeImages = () => {
    if (!items.length) return;
    setAnalyzeStatus("running");
    setAnalyzeProgress("분석 준비 중...");
    setAnalyzeError(null);
    setAnalyses([]);
    setReviewCount(0);

    const ctrl = analyzeItemImages(
      items,
      "",
      (event) => {
        if (event.type === "progress") {
          setAnalyzeProgress(event.step);
          // Accumulate per-item analyses as they arrive
          if (event.data?.analysis) {
            setAnalyses((prev) => {
              const existing = prev.findIndex(
                (a) => a.item_index === event.data!.analysis!.item_index
              );
              if (existing >= 0) {
                const next = [...prev];
                next[existing] = event.data!.analysis!;
                return next;
              }
              return [...prev, event.data!.analysis!];
            });
          }
        } else if (event.type === "done") {
          const finalAnalyses: ItemImageAnalysis[] = event.data?.analyses ?? [];
          const rc = event.data?.review_count ?? 0;
          setAnalyses(finalAnalyses);
          setReviewCount(rc);
          setAnalyzeStatus("done");
          setAnalyzeProgress("");

          // Auto-update items whose best_url differs from current image
          setItems((prev) =>
            prev.map((item, i) => {
              const analysis = finalAnalyses.find((a) => a.item_index === i);
              if (!analysis || !analysis.best_url) return item;
              if (analysis.best_url === item.image_urls?.[0]) return item;
              // Promote best_url to front
              const newUrls = [
                analysis.best_url,
                ...(item.image_urls ?? []).filter((u) => u !== analysis.best_url),
              ];
              return { ...item, image_urls: newUrls, processed_image_path: "" };
            })
          );
        } else if (event.type === "error") {
          setAnalyzeError(event.error || "분석 오류");
          setAnalyzeStatus("error");
        }
      },
      (err) => {
        setAnalyzeError(err);
        setAnalyzeStatus("error");
      }
    );

    analyzeControllerRef.current = ctrl;
  };

  const handleCancelAnalyze = () => {
    analyzeControllerRef.current?.abort();
    cancelPipeline().catch(() => {});
    setAnalyzeStatus("idle");
    setAnalyzeProgress("");
  };

  // Step 4: 블로그 생성
  const handleGenerate = async () => {
    setStep4Status("running");
    setStep4Error(null);
    try {
      const res = await generatePost(items, "", imagePlacement);
      setBlogPost({ celeb: res.celeb, post: res.blog_post });
      setStep4Status("done");
    } catch (e) {
      setStep4Error(String(e));
      setStep4Status("error");
    }
  };

  return (
    <div>
      {/* 공통 설정 */}
      <div style={cardStyle}>
        <h2 style={{ margin: "0 0 16px", fontSize: 15, fontWeight: 700, color: "#1e1b4b" }}>
          공통 설정
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginBottom: 12 }}>
          <div>
            <label style={{ display: "block", fontSize: 12, color: "#6b7280", marginBottom: 5 }}>수집 기간</label>
            <select value={days} onChange={(e) => setDays(Number(e.target.value))} style={inputStyle}>
              {[1, 2, 3, 5, 7].map((d) => <option key={d} value={d}>{d}일</option>)}
            </select>
          </div>
          <div>
            <label style={{ display: "block", fontSize: 12, color: "#6b7280", marginBottom: 5 }}>최대 포스트</label>
            <select value={maxPosts} onChange={(e) => setMaxPosts(Number(e.target.value))} style={inputStyle}>
              {[5, 10, 20, 30].map((n) => <option key={n} value={n}>{n}개</option>)}
            </select>
          </div>
          <div>
            <label style={{ display: "block", fontSize: 12, color: "#6b7280", marginBottom: 5 }}>연예인 수</label>
            <select value={topCelebs} onChange={(e) => setTopCelebs(Number(e.target.value))} style={inputStyle}>
              {[1, 2, 3, 5].map((n) => <option key={n} value={n}>{n}명</option>)}
            </select>
          </div>
        </div>
        <div style={{
          fontSize: 12, color: "#6b7280", background: "#f9fafb",
          border: "1px solid #e5e7eb", borderRadius: 8, padding: "8px 12px",
        }}>
          🔑 OpenAI API 키는 <a href="/settings" style={{ color: "#6366f1", fontWeight: 600 }}>설정</a> 페이지에서 공통으로 관리합니다.
        </div>
      </div>

      {/* Step 1: RSS 수집 */}
      <div style={cardStyle}>
        <StepHeader step={1} title="RSS 수집" status={step1Status} />
        {step1Error && (
          <div style={{ color: "#ef4444", fontSize: 13, marginBottom: 10 }}>⚠️ {step1Error}</div>
        )}
        <RunButton
          onClick={handleCollect}
          disabled={step1Status === "running"}
          loading={step1Status === "running"}
          label="RSS 수집 시작"
        />
        {posts.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <PostsPanel count={posts.length} titles={posts.slice(0, 10).map((p) => p.title)} />
          </div>
        )}
      </div>

      {/* Step 2: 연예인 분석 */}
      <div style={{ ...cardStyle, opacity: step1Status !== "done" ? 0.6 : 1 }}>
        <StepHeader step={2} title="연예인 분석" status={step2Status} />
        {step2Error && (
          <div style={{ color: "#ef4444", fontSize: 13, marginBottom: 10 }}>⚠️ {step2Error}</div>
        )}
        <RunButton
          onClick={handleAnalyze}
          disabled={step1Status !== "done" || step2Status === "running"}
          loading={step2Status === "running"}
          label="연예인 분석"
        />
        {celebs.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <TrendingPanel
              celebs={celebs}
              selected={selectedCeleb}
              onSelect={setSelectedCeleb}
            />
          </div>
        )}
      </div>

      {/* Step 3: 스크랩 + 추출 */}
      <div style={{ ...cardStyle, opacity: step2Status !== "done" ? 0.6 : 1 }}>
        <StepHeader step={3} title="스크랩 + LLM 추출" status={step3Status} />
        {step3Error && (
          <div style={{ color: "#ef4444", fontSize: 13, marginBottom: 10 }}>⚠️ {step3Error}</div>
        )}
        {selectedCeleb && (
          <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 10 }}>
            선택된 연예인: <strong style={{ color: "#7c3aed" }}>{selectedCeleb}</strong>
          </div>
        )}
        <RunButton
          onClick={handleScrape}
          disabled={step2Status !== "done" || step3Status === "running"}
          loading={step3Status === "running"}
          label="스크랩 + 추출"
        />
        {items.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 10 }}>
              총 {items.length}개 아이템 추출됨
            </div>
            <ItemsPanel
              items={items}
              analyses={analyses}
              onUpdateItem={handleUpdateItemImage}
              onRemoveWatermark={handleRemoveWatermark}
            />
          </div>
        )}
      </div>

      {/* Step 3.5: AI 이미지 분석 */}
      <div style={{ ...cardStyle, opacity: step3Status !== "done" ? 0.6 : 1 }}>
        <StepHeader step={3.5 as unknown as number} title="AI 이미지 분석 (선택)" status={analyzeStatus} />

        {analyzeError && (
          <div style={{ color: "#ef4444", fontSize: 13, marginBottom: 10 }}>⚠️ {analyzeError}</div>
        )}

        {analyzeStatus === "running" && analyzeProgress && (
          <div style={{
            fontSize: 13, color: "#7c3aed", background: "#ede9fe",
            borderRadius: 8, padding: "8px 12px", marginBottom: 10,
          }}>
            ⏳ {analyzeProgress}
          </div>
        )}

        {analyzeStatus === "done" && (
          <div style={{
            fontSize: 13, background: reviewCount > 0 ? "#fff7ed" : "#d1fae5",
            color: reviewCount > 0 ? "#c2410c" : "#065f46",
            border: `1px solid ${reviewCount > 0 ? "#fed7aa" : "#a7f3d0"}`,
            borderRadius: 8, padding: "8px 12px", marginBottom: 10,
          }}>
            {reviewCount > 0
              ? `⚠️ ${items.length}개 아이템 중 ${reviewCount}개 검토 필요 — 아래에서 이미지를 직접 선택해주세요`
              : `✅ ${items.length}개 아이템 모두 양호 — AI 추천 이미지로 자동 업데이트됨`}
          </div>
        )}

        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <RunButton
            onClick={handleAnalyzeImages}
            disabled={step3Status !== "done" || analyzeStatus === "running"}
            loading={analyzeStatus === "running"}
            label="AI 이미지 분석 시작"
          />
          {analyzeStatus === "running" && (
            <button
              onClick={handleCancelAnalyze}
              style={{
                padding: "10px 16px", background: "#fee2e2", color: "#dc2626",
                border: "none", borderRadius: 10, fontSize: 13, fontWeight: 600, cursor: "pointer",
              }}
            >
              중단
            </button>
          )}
          {analyzeStatus !== "running" && step3Status === "done" && (
            <span style={{ fontSize: 12, color: "#9ca3af" }}>
              GPT-4o Vision 사용 · 분석 없이 Step 4로 바로 진행 가능
            </span>
          )}
        </div>
      </div>

      {/* Step 4: 블로그 생성 */}
      <div style={{ ...cardStyle, opacity: step3Status !== "done" ? 0.6 : 1 }}>
        <StepHeader step={4} title="블로그 포스트 생성" status={step4Status} />
        {step4Error && (
          <div style={{ color: "#ef4444", fontSize: 13, marginBottom: 10 }}>⚠️ {step4Error}</div>
        )}
        {/* 이미지 배치 선택 */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
          <span style={{ fontSize: 13, color: "#6b7280", fontWeight: 600 }}>이미지 배치:</span>
          {(["두괄식", "미괄식"] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setImagePlacement(mode)}
              style={{
                padding: "6px 16px",
                borderRadius: 8,
                border: "1.5px solid",
                borderColor: imagePlacement === mode ? "#7c3aed" : "#d1d5db",
                background: imagePlacement === mode ? "#ede9fe" : "#fff",
                color: imagePlacement === mode ? "#7c3aed" : "#6b7280",
                fontWeight: 600,
                fontSize: 13,
                cursor: "pointer",
              }}
            >
              {mode === "두괄식" ? "두괄식 (이미지→텍스트)" : "미괄식 (텍스트→이미지)"}
            </button>
          ))}
        </div>
        <RunButton
          onClick={handleGenerate}
          disabled={step3Status !== "done" || step4Status === "running"}
          loading={step4Status === "running"}
          label="블로그 생성"
        />
        {blogPost && (
          <div style={{ marginTop: 16 }}>
            <BlogPostPanel celeb={blogPost.celeb} post={blogPost.post} />
          </div>
        )}
      </div>
    </div>
  );
}
