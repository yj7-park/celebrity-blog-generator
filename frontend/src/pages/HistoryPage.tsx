import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listRuns, getRun, deleteRun } from "../lib/api";
import type { PipelineRun } from "../lib/types";

const cardStyle: React.CSSProperties = {
  background: "#fff",
  border: "1px solid #e5e7eb",
  borderRadius: 16,
  padding: "24px 28px",
  boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
};

function formatDate(iso: string) {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("ko-KR", {
      year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function HistoryPage() {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listRuns()
      .then((r) => setRuns(r.runs))
      .catch(() => setError("히스토리를 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }, []);

  const handleLoad = async (run: PipelineRun) => {
    setLoadingId(run.id);
    try {
      const full = await getRun(run.id);
      navigate("/dashboard", { state: { loadedRun: full } });
    } catch {
      setError("데이터를 불러오지 못했습니다.");
    } finally {
      setLoadingId(null);
    }
  };

  const handleDelete = async (run: PipelineRun) => {
    if (!window.confirm(`"${run.celeb}" 데이터를 삭제할까요?`)) return;
    setDeletingId(run.id);
    try {
      await deleteRun(run.id);
      setRuns((prev) => prev.filter((r) => r.id !== run.id));
    } catch {
      setError("삭제에 실패했습니다.");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={cardStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: "#1e1b4b" }}>
            파이프라인 히스토리
          </h2>
          <span style={{ fontSize: 13, color: "#6b7280" }}>
            {runs.length}개 저장됨
          </span>
        </div>

        {error && (
          <div style={{
            background: "#fef2f2", border: "1px solid #fecaca",
            borderRadius: 8, padding: "10px 14px", color: "#dc2626",
            fontSize: 13, marginBottom: 16,
          }}>
            ⚠️ {error}
          </div>
        )}

        {loading ? (
          <div style={{ textAlign: "center", padding: "40px 0", color: "#9ca3af", fontSize: 14 }}>
            불러오는 중...
          </div>
        ) : runs.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px 0", color: "#9ca3af", fontSize: 14 }}>
            저장된 실행 결과가 없습니다.<br />
            <span style={{ fontSize: 12 }}>대시보드에서 파이프라인을 실행하면 자동으로 저장됩니다.</span>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {/* 헤더 */}
            <div style={{
              display: "grid",
              gridTemplateColumns: "120px 1fr 80px 80px 160px",
              gap: 12,
              padding: "8px 12px",
              fontSize: 11,
              fontWeight: 600,
              color: "#9ca3af",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              borderBottom: "1px solid #f3f4f6",
            }}>
              <span>연예인</span>
              <span>블로그 제목</span>
              <span style={{ textAlign: "center" }}>아이템</span>
              <span style={{ textAlign: "center" }}>날짜</span>
              <span style={{ textAlign: "right" }}>작업</span>
            </div>

            {/* 행 */}
            {runs.map((run) => (
              <div
                key={run.id}
                style={{
                  display: "grid",
                  gridTemplateColumns: "120px 1fr 80px 80px 160px",
                  gap: 12,
                  padding: "12px 12px",
                  borderRadius: 10,
                  background: "#fafafa",
                  border: "1px solid #f3f4f6",
                  alignItems: "center",
                  transition: "background 0.15s",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "#f5f3ff")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "#fafafa")}
              >
                {/* 연예인 */}
                <span style={{
                  fontSize: 14, fontWeight: 700, color: "#1e1b4b",
                  overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                }}>
                  {run.celeb}
                </span>

                {/* 제목 */}
                <span style={{
                  fontSize: 13, color: "#374151",
                  overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                }}>
                  {run.title || <span style={{ color: "#9ca3af" }}>제목 없음</span>}
                </span>

                {/* 아이템 수 */}
                <span style={{
                  textAlign: "center", fontSize: 13, fontWeight: 600,
                  color: "#7c3aed",
                }}>
                  {run.item_count}개
                </span>

                {/* 날짜 */}
                <span style={{ textAlign: "center", fontSize: 11, color: "#6b7280" }}>
                  {formatDate(run.created_at)}
                </span>

                {/* 액션 버튼 */}
                <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                  <button
                    onClick={() => handleLoad(run)}
                    disabled={loadingId === run.id}
                    style={{
                      padding: "5px 12px", fontSize: 12, fontWeight: 600,
                      background: loadingId === run.id ? "#e0e7ff" : "#ede9fe",
                      color: "#6366f1", border: "none", borderRadius: 7,
                      cursor: loadingId === run.id ? "not-allowed" : "pointer",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {loadingId === run.id ? "로딩..." : "불러오기"}
                  </button>
                  <button
                    onClick={() => handleDelete(run)}
                    disabled={deletingId === run.id}
                    style={{
                      padding: "5px 12px", fontSize: 12, fontWeight: 600,
                      background: "#fef2f2", color: "#dc2626",
                      border: "none", borderRadius: 7,
                      cursor: deletingId === run.id ? "not-allowed" : "pointer",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {deletingId === run.id ? "삭제 중..." : "삭제"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
