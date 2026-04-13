import { useState, useEffect, useRef } from "react";
import { writeNaverBlog, getNaverStatus, getSettings } from "../lib/api";

type ElementType = "text" | "header" | "url" | "url_text";

interface BlogElement {
  id: string;
  type: ElementType;
  content: string;
  text?: string; // url_text 타입의 링크 텍스트
}

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
  marginBottom: 16,
};

const ELEMENT_TYPE_LABELS: Record<ElementType, string> = {
  text: "본문 텍스트",
  header: "소제목",
  url: "링크 URL",
  url_text: "링크 텍스트",
};

let idCounter = 0;
function genId() {
  return `el_${Date.now()}_${idCounter++}`;
}

export default function BlogWriterPage() {
  const [title, setTitle] = useState("");
  const [elements, setElements] = useState<BlogElement[]>([
    { id: genId(), type: "text", content: "" },
  ]);
  const [tags, setTags] = useState("");
  const [naverLogin, setNaverLogin] = useState<string | null>(null);

  const [publishing, setPublishing] = useState(false);
  const [publishError, setPublishError] = useState<string | null>(null);
  const [publishedUrl, setPublishedUrl] = useState<string | null>(null);
  const [publishStatus, setPublishStatus] = useState<string | null>(null);

  const pollingRef = useRef<number | null>(null);

  useEffect(() => {
    getSettings()
      .then((s) => setNaverLogin(s.naver_id || null))
      .catch(() => setNaverLogin(null));
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  const addElement = (type: ElementType) => {
    setElements((prev) => [...prev, { id: genId(), type, content: "", text: "" }]);
  };

  const removeElement = (id: string) => {
    setElements((prev) => prev.filter((e) => e.id !== id));
  };

  const updateElement = (id: string, field: keyof BlogElement, value: string) => {
    setElements((prev) =>
      prev.map((e) => (e.id === id ? { ...e, [field]: value } : e))
    );
  };

  const moveUp = (index: number) => {
    if (index === 0) return;
    setElements((prev) => {
      const next = [...prev];
      [next[index - 1], next[index]] = [next[index], next[index - 1]];
      return next;
    });
  };

  const moveDown = (index: number) => {
    setElements((prev) => {
      if (index >= prev.length - 1) return prev;
      const next = [...prev];
      [next[index], next[index + 1]] = [next[index + 1], next[index]];
      return next;
    });
  };

  const startPolling = () => {
    pollingRef.current = window.setInterval(async () => {
      try {
        const res = await getNaverStatus();
        setPublishStatus(res.status);
        if (res.status === "done" || res.url) {
          setPublishedUrl(res.url ?? null);
          setPublishing(false);
          if (pollingRef.current) clearInterval(pollingRef.current);
        } else if (res.status === "error") {
          setPublishError(res.error ?? "발행 중 오류 발생");
          setPublishing(false);
          if (pollingRef.current) clearInterval(pollingRef.current);
        }
      } catch {
        // 폴링 오류 무시
      }
    }, 2000);
  };

  const handlePublish = async () => {
    if (!title.trim()) { setPublishError("제목을 입력해주세요."); return; }
    if (elements.every((e) => !e.content.trim())) { setPublishError("내용을 입력해주세요."); return; }

    setPublishing(true);
    setPublishError(null);
    setPublishedUrl(null);
    setPublishStatus("발행 시작...");

    const tagList = tags
      .split(/[,\s]+/)
      .map((t) => t.trim())
      .filter(Boolean);

    const elems = elements.map((e) => ({
      type: e.type,
      content: e.content,
      ...(e.type === "url_text" ? { text: e.text } : {}),
    }));

    try {
      const res = await writeNaverBlog(title, elems, tagList);
      if (res.blog_url) {
        setPublishedUrl(res.blog_url);
        setPublishStatus("완료");
        setPublishing(false);
      } else if (res.error) {
        setPublishError(res.error);
        setPublishing(false);
      } else {
        startPolling();
      }
    } catch (e) {
      setPublishError(String(e));
      setPublishing(false);
    }
  };

  return (
    <div>
      {/* 제목 */}
      <div style={cardStyle}>
        <h2 style={{ margin: "0 0 16px", fontSize: 15, fontWeight: 700, color: "#1e1b4b" }}>
          블로그 제목
        </h2>
        <input
          type="text"
          placeholder="블로그 포스트 제목 입력"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          style={{ ...inputStyle, fontSize: 16 }}
        />
      </div>

      {/* 본문 요소 편집기 */}
      <div style={cardStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h2 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: "#1e1b4b" }}>
            본문 요소
          </h2>
          <div style={{ display: "flex", gap: 6 }}>
            {(Object.keys(ELEMENT_TYPE_LABELS) as ElementType[]).map((type) => (
              <button
                key={type}
                onClick={() => addElement(type)}
                style={{
                  padding: "6px 12px",
                  background: "#ede9fe",
                  color: "#7c3aed",
                  border: "none",
                  borderRadius: 8,
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                + {ELEMENT_TYPE_LABELS[type]}
              </button>
            ))}
          </div>
        </div>

        {elements.length === 0 && (
          <div style={{ textAlign: "center", color: "#9ca3af", fontSize: 14, padding: "20px 0" }}>
            위 버튼을 클릭하여 요소를 추가하세요.
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {elements.map((el, index) => (
            <div
              key={el.id}
              style={{
                border: "1px solid #e5e7eb",
                borderRadius: 10,
                padding: "12px 14px",
                background: "#f9fafb",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    color: "#7c3aed",
                    background: "#ede9fe",
                    padding: "2px 8px",
                    borderRadius: 4,
                  }}
                >
                  {ELEMENT_TYPE_LABELS[el.type]}
                </span>
                <div style={{ flex: 1 }} />
                <button
                  onClick={() => moveUp(index)}
                  disabled={index === 0}
                  style={{
                    padding: "2px 8px",
                    background: "none",
                    border: "1px solid #d1d5db",
                    borderRadius: 4,
                    cursor: index === 0 ? "not-allowed" : "pointer",
                    fontSize: 12,
                    color: "#6b7280",
                  }}
                >
                  ▲
                </button>
                <button
                  onClick={() => moveDown(index)}
                  disabled={index === elements.length - 1}
                  style={{
                    padding: "2px 8px",
                    background: "none",
                    border: "1px solid #d1d5db",
                    borderRadius: 4,
                    cursor: index === elements.length - 1 ? "not-allowed" : "pointer",
                    fontSize: 12,
                    color: "#6b7280",
                  }}
                >
                  ▼
                </button>
                <button
                  onClick={() => removeElement(el.id)}
                  style={{
                    padding: "2px 8px",
                    background: "#fee2e2",
                    border: "none",
                    borderRadius: 4,
                    cursor: "pointer",
                    fontSize: 12,
                    color: "#ef4444",
                    fontWeight: 600,
                  }}
                >
                  삭제
                </button>
              </div>

              {el.type === "text" && (
                <textarea
                  placeholder="본문 내용 입력..."
                  value={el.content}
                  onChange={(e) => updateElement(el.id, "content", e.target.value)}
                  rows={4}
                  style={{
                    ...inputStyle,
                    resize: "vertical",
                    fontFamily: "inherit",
                    lineHeight: 1.6,
                  }}
                />
              )}

              {el.type === "header" && (
                <input
                  type="text"
                  placeholder="소제목 입력..."
                  value={el.content}
                  onChange={(e) => updateElement(el.id, "content", e.target.value)}
                  style={{ ...inputStyle, fontWeight: 600 }}
                />
              )}

              {el.type === "url" && (
                <input
                  type="url"
                  placeholder="https://..."
                  value={el.content}
                  onChange={(e) => updateElement(el.id, "content", e.target.value)}
                  style={{ ...inputStyle, color: "#6366f1" }}
                />
              )}

              {el.type === "url_text" && (
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <input
                    type="text"
                    placeholder="링크 텍스트..."
                    value={el.text ?? ""}
                    onChange={(e) => updateElement(el.id, "text", e.target.value)}
                    style={inputStyle}
                  />
                  <input
                    type="url"
                    placeholder="https://..."
                    value={el.content}
                    onChange={(e) => updateElement(el.id, "content", e.target.value)}
                    style={{ ...inputStyle, color: "#6366f1" }}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 태그 */}
      <div style={cardStyle}>
        <h2 style={{ margin: "0 0 12px", fontSize: 15, fontWeight: 700, color: "#1e1b4b" }}>
          태그
        </h2>
        <input
          type="text"
          placeholder="태그를 쉼표 또는 공백으로 구분 (예: 패션, 뷰티, 아이유)"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          style={inputStyle}
        />
      </div>

      {/* 네이버 발행 */}
      <div style={cardStyle}>
        <h2 style={{ margin: "0 0 16px", fontSize: 15, fontWeight: 700, color: "#1e1b4b" }}>
          네이버 블로그 발행
        </h2>

        {/* 로그인 상태 */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            marginBottom: 16,
            padding: "10px 14px",
            background: naverLogin ? "#d1fae5" : "#fef3c7",
            borderRadius: 8,
          }}
        >
          <span style={{ fontSize: 16 }}>{naverLogin ? "✅" : "⚠️"}</span>
          <span style={{ fontSize: 13, fontWeight: 500, color: naverLogin ? "#065f46" : "#92400e" }}>
            {naverLogin
              ? `네이버 계정: ${naverLogin} (로그인됨)`
              : "네이버 계정이 설정되지 않았습니다. 설정 페이지에서 입력해주세요."}
          </span>
        </div>

        {publishError && (
          <div
            style={{
              background: "#fef2f2",
              border: "1px solid #fecaca",
              borderRadius: 8,
              padding: "10px 14px",
              color: "#dc2626",
              fontSize: 13,
              marginBottom: 12,
            }}
          >
            ⚠️ {publishError}
          </div>
        )}

        {publishStatus && !publishedUrl && (
          <div
            style={{
              background: "#ede9fe",
              borderRadius: 8,
              padding: "10px 14px",
              fontSize: 13,
              color: "#7c3aed",
              marginBottom: 12,
            }}
          >
            ⏳ {publishStatus}
          </div>
        )}

        {publishedUrl && (
          <div
            style={{
              background: "#d1fae5",
              border: "1px solid #a7f3d0",
              borderRadius: 8,
              padding: "12px 16px",
              marginBottom: 12,
            }}
          >
            <div style={{ fontSize: 13, fontWeight: 600, color: "#065f46", marginBottom: 6 }}>
              ✅ 발행 완료!
            </div>
            <a
              href={publishedUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{ fontSize: 13, color: "#6366f1", wordBreak: "break-all" }}
            >
              {publishedUrl}
            </a>
          </div>
        )}

        <button
          onClick={handlePublish}
          disabled={publishing || !naverLogin}
          style={{
            padding: "12px 28px",
            background:
              publishing || !naverLogin
                ? "#a5b4fc"
                : "linear-gradient(90deg, #6366f1, #8b5cf6)",
            color: "#fff",
            border: "none",
            borderRadius: 10,
            fontSize: 15,
            fontWeight: 600,
            cursor: publishing || !naverLogin ? "not-allowed" : "pointer",
          }}
        >
          {publishing ? "⏳ 발행 중..." : "네이버 블로그에 발행"}
        </button>
      </div>
    </div>
  );
}
