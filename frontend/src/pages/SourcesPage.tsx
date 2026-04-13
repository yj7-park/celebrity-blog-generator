import { useState, useEffect } from "react";
import { listSources, createSource, updateSource, deleteSource } from "../lib/api";
import type { BlogSource } from "../lib/types";

const cardStyle: React.CSSProperties = {
  background: "#fff",
  border: "1px solid #e5e7eb",
  borderRadius: 16,
  padding: "24px 28px",
  boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
  marginBottom: 16,
};

const inputStyle: React.CSSProperties = {
  padding: "9px 13px",
  border: "1px solid #d1d5db",
  borderRadius: 9,
  fontSize: 13,
  outline: "none",
  width: "100%",
  boxSizing: "border-box",
};

const MAPPING_OPTIONS = [
  { value: "두괄식", label: "두괄식 (텍스트 → 이미지)", desc: "제품 설명 아래에 이미지" },
  { value: "미괄식", label: "미괄식 (이미지 → 텍스트)", desc: "이미지 아래에 제품 설명" },
];

function formatDate(iso: string | null): string {
  if (!iso) return "없음";
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

interface SourceFormData {
  name: string;
  url: string;
  image_mapping: string;
  active: boolean;
  notes: string;
}

const EMPTY_FORM: SourceFormData = {
  name: "",
  url: "",
  image_mapping: "두괄식",
  active: true,
  notes: "",
};

export default function SourcesPage() {
  const [sources, setSources] = useState<BlogSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Add/Edit form
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<SourceFormData>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Delete confirm
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const load = async () => {
    try {
      const data = await listSources();
      setSources(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const openAdd = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setFormError(null);
    setShowForm(true);
  };

  const openEdit = (src: BlogSource) => {
    setEditingId(src.id);
    setForm({
      name: src.name,
      url: src.url,
      image_mapping: src.image_mapping,
      active: src.active,
      notes: src.notes,
    });
    setFormError(null);
    setShowForm(true);
  };

  const handleSave = async () => {
    if (!form.name.trim()) { setFormError("이름을 입력해주세요."); return; }
    if (!form.url.trim()) { setFormError("URL을 입력해주세요."); return; }

    setSaving(true);
    setFormError(null);
    try {
      if (editingId) {
        const updated = await updateSource(editingId, form);
        setSources((prev) => prev.map((s) => s.id === editingId ? updated : s));
      } else {
        const created = await createSource(form);
        setSources((prev) => [created, ...prev]);
      }
      setShowForm(false);
    } catch (e) {
      setFormError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleToggleActive = async (src: BlogSource) => {
    try {
      const updated = await updateSource(src.id, { active: !src.active });
      setSources((prev) => prev.map((s) => s.id === src.id ? updated : s));
    } catch {
      // silently ignore
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteSource(id);
      setSources((prev) => prev.filter((s) => s.id !== id));
    } catch (e) {
      setError(String(e));
    } finally {
      setDeletingId(null);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 60, color: "#9ca3af", fontSize: 14 }}>
        불러오는 중...
      </div>
    );
  }

  return (
    <div>
      {error && (
        <div style={{
          background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 10,
          padding: "12px 16px", color: "#dc2626", fontSize: 13, marginBottom: 16,
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* Header */}
      <div style={{ ...cardStyle, padding: "20px 28px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2 style={{ margin: "0 0 4px", fontSize: 15, fontWeight: 700, color: "#1e1b4b" }}>
              소스 블로그 관리
            </h2>
            <p style={{ margin: 0, fontSize: 13, color: "#6b7280" }}>
              스크랩할 네이버 블로그를 등록하고 이미지-아이템 매핑 패턴을 설정합니다.
            </p>
          </div>
          <button
            onClick={openAdd}
            style={{
              padding: "10px 20px", background: "linear-gradient(90deg, #6366f1, #8b5cf6)",
              color: "#fff", border: "none", borderRadius: 10,
              fontSize: 13, fontWeight: 600, cursor: "pointer", whiteSpace: "nowrap",
            }}
          >
            + 소스 추가
          </button>
        </div>
      </div>

      {/* Add/Edit Form */}
      {showForm && (
        <div style={{ ...cardStyle, border: "1px solid #a5b4fc" }}>
          <h3 style={{ margin: "0 0 16px", fontSize: 14, fontWeight: 700, color: "#1e1b4b" }}>
            {editingId ? "소스 수정" : "새 소스 추가"}
          </h3>

          {formError && (
            <div style={{
              background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8,
              padding: "8px 12px", color: "#dc2626", fontSize: 12, marginBottom: 12,
            }}>
              {formError}
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#374151", marginBottom: 5 }}>
                블로그 이름 *
              </label>
              <input
                type="text"
                placeholder="예: 스타일온더스트릿"
                value={form.name}
                onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                style={inputStyle}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#374151", marginBottom: 5 }}>
                블로그 URL *
              </label>
              <input
                type="url"
                placeholder="예: https://blog.naver.com/myblog"
                value={form.url}
                onChange={(e) => setForm((p) => ({ ...p, url: e.target.value }))}
                style={inputStyle}
              />
            </div>
          </div>

          {/* Image mapping selector */}
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#374151", marginBottom: 8 }}>
              이미지 배치 패턴
            </label>
            <div style={{ display: "flex", gap: 10 }}>
              {MAPPING_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setForm((p) => ({ ...p, image_mapping: opt.value }))}
                  style={{
                    flex: 1, padding: "12px 16px", textAlign: "left",
                    borderRadius: 10,
                    border: form.image_mapping === opt.value
                      ? "2px solid #7c3aed"
                      : "1.5px solid #e5e7eb",
                    background: form.image_mapping === opt.value ? "#ede9fe" : "#fff",
                    cursor: "pointer",
                  }}
                >
                  <div style={{
                    fontSize: 13, fontWeight: 700,
                    color: form.image_mapping === opt.value ? "#7c3aed" : "#374151",
                    marginBottom: 3,
                  }}>
                    {opt.label}
                  </div>
                  <div style={{ fontSize: 11, color: "#6b7280" }}>{opt.desc}</div>
                  {/* Visual diagram */}
                  <div style={{ marginTop: 8, display: "flex", gap: 4, alignItems: "center" }}>
                    {opt.value === "두괄식" ? (
                      <>
                        <div style={{ ...blockPreview, background: "#dbeafe", color: "#1d4ed8" }}>텍스트</div>
                        <span style={{ fontSize: 10, color: "#9ca3af" }}>→</span>
                        <div style={{ ...blockPreview, background: "#fce7f3", color: "#be185d" }}>이미지</div>
                      </>
                    ) : (
                      <>
                        <div style={{ ...blockPreview, background: "#fce7f3", color: "#be185d" }}>이미지</div>
                        <span style={{ fontSize: 10, color: "#9ca3af" }}>→</span>
                        <div style={{ ...blockPreview, background: "#dbeafe", color: "#1d4ed8" }}>텍스트</div>
                      </>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#374151", marginBottom: 5 }}>
              메모 (선택)
            </label>
            <input
              type="text"
              placeholder="참고 사항 입력..."
              value={form.notes}
              onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))}
              style={inputStyle}
            />
          </div>

          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={form.active}
                onChange={(e) => setForm((p) => ({ ...p, active: e.target.checked }))}
              />
              활성화
            </label>
            <div style={{ flex: 1 }} />
            <button
              onClick={() => setShowForm(false)}
              style={{
                padding: "9px 18px", background: "#f3f4f6", color: "#374151",
                border: "none", borderRadius: 9, fontSize: 13, fontWeight: 600, cursor: "pointer",
              }}
            >
              취소
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              style={{
                padding: "9px 20px",
                background: saving ? "#a5b4fc" : "linear-gradient(90deg, #6366f1, #8b5cf6)",
                color: "#fff", border: "none", borderRadius: 9,
                fontSize: 13, fontWeight: 600, cursor: saving ? "not-allowed" : "pointer",
              }}
            >
              {saving ? "저장 중..." : (editingId ? "수정 저장" : "추가")}
            </button>
          </div>
        </div>
      )}

      {/* Source list */}
      {sources.length === 0 ? (
        <div style={{
          ...cardStyle, textAlign: "center", color: "#9ca3af",
          fontSize: 14, padding: "40px 28px",
        }}>
          등록된 소스 블로그가 없습니다. 위에서 추가해주세요.
        </div>
      ) : (
        <div style={cardStyle}>
          <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 12 }}>
            총 {sources.length}개 소스 (활성: {sources.filter((s) => s.active).length}개)
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
            {sources.map((src, i) => (
              <div key={src.id}>
                {i > 0 && <div style={{ height: 1, background: "#f3f4f6", margin: "4px 0" }} />}
                <div style={{
                  display: "flex", gap: 14, alignItems: "center",
                  padding: "12px 4px",
                  opacity: src.active ? 1 : 0.55,
                }}>
                  {/* Active toggle */}
                  <div
                    onClick={() => handleToggleActive(src)}
                    title={src.active ? "비활성화" : "활성화"}
                    style={{
                      width: 10, height: 10, borderRadius: "50%", flexShrink: 0, cursor: "pointer",
                      background: src.active ? "#10b981" : "#d1d5db",
                    }}
                  />

                  {/* Info */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 3 }}>
                      <span style={{ fontSize: 14, fontWeight: 700, color: "#1e1b4b" }}>
                        {src.name}
                      </span>
                      {/* Mapping badge */}
                      <span style={{
                        fontSize: 11, fontWeight: 600, padding: "1px 8px", borderRadius: 99,
                        background: src.image_mapping === "미괄식" ? "#fce7f3" : "#dbeafe",
                        color: src.image_mapping === "미괄식" ? "#be185d" : "#1d4ed8",
                      }}>
                        {src.image_mapping}
                      </span>
                      {!src.active && (
                        <span style={{
                          fontSize: 10, fontWeight: 600, padding: "1px 6px", borderRadius: 99,
                          background: "#f3f4f6", color: "#9ca3af",
                        }}>
                          비활성
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 12, color: "#6366f1", marginBottom: 2, wordBreak: "break-all" }}>
                      {src.url}
                    </div>
                    <div style={{ display: "flex", gap: 16, fontSize: 11, color: "#9ca3af" }}>
                      <span>등록: {formatDate(src.created_at)}</span>
                      <span>최근 스크랩: {formatDate(src.last_scraped_at)}</span>
                    </div>
                    {src.notes && (
                      <div style={{ fontSize: 11, color: "#6b7280", marginTop: 3, fontStyle: "italic" }}>
                        {src.notes}
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                    <button
                      onClick={() => openEdit(src)}
                      style={{
                        padding: "6px 12px", background: "#f3f4f6", color: "#374151",
                        border: "none", borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: "pointer",
                      }}
                    >
                      수정
                    </button>
                    {deletingId === src.id ? (
                      <>
                        <button
                          onClick={() => handleDelete(src.id)}
                          style={{
                            padding: "6px 12px", background: "#fef2f2", color: "#dc2626",
                            border: "1px solid #fecaca", borderRadius: 8,
                            fontSize: 12, fontWeight: 700, cursor: "pointer",
                          }}
                        >
                          삭제 확인
                        </button>
                        <button
                          onClick={() => setDeletingId(null)}
                          style={{
                            padding: "6px 10px", background: "#f3f4f6", color: "#6b7280",
                            border: "none", borderRadius: 8, fontSize: 12, cursor: "pointer",
                          }}
                        >
                          취소
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => setDeletingId(src.id)}
                        style={{
                          padding: "6px 10px", background: "#fff", color: "#ef4444",
                          border: "1px solid #fecaca", borderRadius: 8,
                          fontSize: 12, fontWeight: 600, cursor: "pointer",
                        }}
                      >
                        삭제
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Guide */}
      <div style={{
        ...cardStyle,
        background: "#f8f7ff",
        border: "1px solid #e0e7ff",
      }}>
        <h3 style={{ margin: "0 0 10px", fontSize: 13, fontWeight: 700, color: "#4338ca" }}>
          이미지 배치 패턴이란?
        </h3>
        <div style={{ fontSize: 12, color: "#4b5563", lineHeight: 1.8 }}>
          <p style={{ margin: "0 0 8px" }}>
            <strong>두괄식</strong> — 블로거가 제품 설명(브랜드명·가격 등)을 먼저 쓰고 그 아래에 이미지를 올리는 패턴입니다.<br />
            스크랩 시 텍스트 블록 <strong>뒤에 오는</strong> 이미지를 해당 아이템과 매핑합니다.
          </p>
          <p style={{ margin: 0 }}>
            <strong>미괄식</strong> — 블로거가 이미지를 먼저 올리고 아래에 제품 설명을 쓰는 패턴입니다.<br />
            스크랩 시 텍스트 블록 <strong>앞에 오는</strong> 이미지를 해당 아이템과 매핑합니다.
          </p>
        </div>
      </div>
    </div>
  );
}

const blockPreview: React.CSSProperties = {
  fontSize: 10, fontWeight: 600, padding: "3px 8px",
  borderRadius: 6, whiteSpace: "nowrap",
};
