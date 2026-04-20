import { useState, useEffect } from "react";
import {
  getSchedulerJobs,
  createSchedulerJob,
  updateSchedulerJob,
  deleteSchedulerJob,
  triggerSchedulerJob,
} from "../lib/api";
import type { ScheduleJob } from "../lib/types";

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

const CRON_PRESETS = [
  { label: "매일 오전 9시", value: "0 9 * * *" },
  { label: "매일 오후 6시", value: "0 18 * * *" },
  { label: "매주 월요일 오전 9시", value: "0 9 * * 1" },
  { label: "매주 금요일 오후 6시", value: "0 18 * * 5" },
  { label: "매일 자정", value: "0 0 * * *" },
  { label: "직접 입력", value: "custom" },
];

interface JobForm {
  name: string;
  cron: string;
  cronCustom: string;
  cronPreset: string;
  enabled: boolean;
  days: number;
  max_posts: number;
  top_celebs: number;
  auto_publish: boolean;
}

const DEFAULT_FORM: JobForm = {
  name: "",
  cron: "0 9 * * *",
  cronCustom: "",
  cronPreset: "0 9 * * *",
  enabled: true,
  days: 2,
  max_posts: 10,
  top_celebs: 3,
  auto_publish: false,
};

function formatDateTime(s?: string) {
  if (!s) return "-";
  try {
    return new Date(s).toLocaleString("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return s;
  }
}

export default function SchedulerPage() {
  const [jobs, setJobs] = useState<ScheduleJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<JobForm>(DEFAULT_FORM);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const [triggeringId, setTriggeringId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const loadJobs = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getSchedulerJobs();
      setJobs(res.jobs ?? []);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
  }, []);

  const handlePresetChange = (preset: string) => {
    if (preset === "custom") {
      setForm((f) => ({ ...f, cronPreset: "custom", cron: f.cronCustom }));
    } else {
      setForm((f) => ({ ...f, cronPreset: preset, cron: preset }));
    }
  };

  const handleSave = async () => {
    if (!form.name.trim()) { setSaveError("스케줄 이름을 입력해주세요."); return; }
    if (!form.cron.trim()) { setSaveError("cron 표현식을 입력해주세요."); return; }

    setSaving(true);
    setSaveError(null);
    try {
      await createSchedulerJob({
        name: form.name,
        cron: form.cron,
        enabled: form.enabled,
        days: form.days,
        max_posts: form.max_posts,
        top_celebs: form.top_celebs,
        auto_publish: form.auto_publish,
      });
      setShowForm(false);
      setForm(DEFAULT_FORM);
      await loadJobs();
    } catch (e) {
      setSaveError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleToggleEnabled = async (job: ScheduleJob) => {
    try {
      await updateSchedulerJob(job.id, { enabled: !job.enabled });
      await loadJobs();
    } catch (e) {
      alert(`수정 실패: ${e}`);
    }
  };

  const handleTrigger = async (job: ScheduleJob) => {
    setTriggeringId(job.id);
    try {
      await triggerSchedulerJob(job.id);
      alert(`"${job.name}" 즉시 실행을 요청했습니다.`);
    } catch (e) {
      alert(`실행 실패: ${e}`);
    } finally {
      setTriggeringId(null);
    }
  };

  const handleDelete = async (job: ScheduleJob) => {
    if (!confirm(`"${job.name}" 스케줄을 삭제하시겠습니까?`)) return;
    setDeletingId(job.id);
    try {
      await deleteSchedulerJob(job.id);
      await loadJobs();
    } catch (e) {
      alert(`삭제 실패: ${e}`);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div>
      {/* 헤더 */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div style={{ fontSize: 14, color: "#6b7280" }}>
          등록된 스케줄: <strong>{jobs.length}개</strong>
        </div>
        <button
          onClick={() => { setShowForm(!showForm); setSaveError(null); }}
          style={{
            padding: "10px 20px",
            background: showForm ? "#fee2e2" : "linear-gradient(90deg, #6366f1, #8b5cf6)",
            color: showForm ? "#dc2626" : "#fff",
            border: "none",
            borderRadius: 10,
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {showForm ? "취소" : "+ 새 스케줄 추가"}
        </button>
      </div>

      {/* 새 스케줄 폼 */}
      {showForm && (
        <div style={cardStyle}>
          <h2 style={{ margin: "0 0 20px", fontSize: 15, fontWeight: 700, color: "#1e1b4b" }}>
            새 스케줄 추가
          </h2>

          {saveError && (
            <div style={{ color: "#ef4444", fontSize: 13, marginBottom: 12, background: "#fef2f2", padding: "8px 12px", borderRadius: 8 }}>
              ⚠️ {saveError}
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div>
              <label style={{ display: "block", fontSize: 12, color: "#6b7280", marginBottom: 5 }}>스케줄 이름</label>
              <input
                type="text"
                placeholder="예: 매일 오전 블로그 생성"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                style={inputStyle}
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: 12, color: "#6b7280", marginBottom: 5 }}>실행 시간</label>
              <select
                value={form.cronPreset}
                onChange={(e) => handlePresetChange(e.target.value)}
                style={inputStyle}
              >
                {CRON_PRESETS.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
              {form.cronPreset === "custom" && (
                <input
                  type="text"
                  placeholder="cron 표현식 (예: 0 9 * * *)"
                  value={form.cronCustom}
                  onChange={(e) => setForm((f) => ({ ...f, cronCustom: e.target.value, cron: e.target.value }))}
                  style={{ ...inputStyle, marginTop: 8 }}
                />
              )}
              <div style={{ fontSize: 11, color: "#9ca3af", marginTop: 4 }}>
                선택된 cron: <code style={{ background: "#f3f4f6", padding: "1px 6px", borderRadius: 4 }}>{form.cron}</code>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
              <div>
                <label style={{ display: "block", fontSize: 12, color: "#6b7280", marginBottom: 5 }}>수집 기간 (일)</label>
                <select value={form.days} onChange={(e) => setForm((f) => ({ ...f, days: Number(e.target.value) }))} style={inputStyle}>
                  {[1, 2, 3, 5, 7].map((d) => <option key={d} value={d}>{d}일</option>)}
                </select>
              </div>
              <div>
                <label style={{ display: "block", fontSize: 12, color: "#6b7280", marginBottom: 5 }}>최대 포스트 수</label>
                <select value={form.max_posts} onChange={(e) => setForm((f) => ({ ...f, max_posts: Number(e.target.value) }))} style={inputStyle}>
                  {[5, 10, 20, 30].map((n) => <option key={n} value={n}>{n}개</option>)}
                </select>
              </div>
              <div>
                <label style={{ display: "block", fontSize: 12, color: "#6b7280", marginBottom: 5 }}>연예인 수</label>
                <select value={form.top_celebs} onChange={(e) => setForm((f) => ({ ...f, top_celebs: Number(e.target.value) }))} style={inputStyle}>
                  {[1, 2, 3, 5].map((n) => <option key={n} value={n}>{n}명</option>)}
                </select>
              </div>
            </div>

            <div style={{ display: "flex", gap: 24 }}>
              <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: 14 }}>
                <input
                  type="checkbox"
                  checked={form.enabled}
                  onChange={(e) => setForm((f) => ({ ...f, enabled: e.target.checked }))}
                  style={{ width: 16, height: 16 }}
                />
                활성화
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: 14 }}>
                <input
                  type="checkbox"
                  checked={form.auto_publish}
                  onChange={(e) => setForm((f) => ({ ...f, auto_publish: e.target.checked }))}
                  style={{ width: 16, height: 16 }}
                />
                네이버 자동 발행
              </label>
            </div>

            <div style={{ display: "flex", gap: 10 }}>
              <button
                onClick={handleSave}
                disabled={saving}
                style={{
                  padding: "11px 24px",
                  background: saving ? "#a5b4fc" : "linear-gradient(90deg, #6366f1, #8b5cf6)",
                  color: "#fff",
                  border: "none",
                  borderRadius: 10,
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: saving ? "not-allowed" : "pointer",
                }}
              >
                {saving ? "저장 중..." : "저장"}
              </button>
              <button
                onClick={() => { setShowForm(false); setForm(DEFAULT_FORM); setSaveError(null); }}
                style={{
                  padding: "11px 24px",
                  background: "#f3f4f6",
                  color: "#374151",
                  border: "none",
                  borderRadius: 10,
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                취소
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 에러 */}
      {error && (
        <div style={{ color: "#ef4444", fontSize: 13, marginBottom: 12, background: "#fef2f2", padding: "10px 14px", borderRadius: 8 }}>
          ⚠️ {error}
        </div>
      )}

      {/* 목록 */}
      {loading ? (
        <div style={{ textAlign: "center", padding: "40px", color: "#9ca3af", fontSize: 14 }}>
          스케줄 목록 불러오는 중...
        </div>
      ) : jobs.length === 0 ? (
        <div style={{ ...cardStyle, textAlign: "center", padding: "60px 20px", color: "#9ca3af", fontSize: 14 }}>
          등록된 스케줄이 없습니다. 위 버튼을 클릭하여 스케줄을 추가하세요.
        </div>
      ) : (
        <div style={cardStyle}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "2px solid #e5e7eb" }}>
                  {["이름", "Cron", "활성화", "설정", "마지막 실행", "다음 실행", "액션"].map((h) => (
                    <th
                      key={h}
                      style={{
                        padding: "10px 12px",
                        textAlign: "left",
                        color: "#6b7280",
                        fontWeight: 600,
                        whiteSpace: "nowrap",
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr
                    key={job.id}
                    style={{
                      borderBottom: "1px solid #f3f4f6",
                      transition: "background 0.1s",
                    }}
                    onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = "#f9fafb")}
                    onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = "")}
                  >
                    <td style={{ padding: "12px 12px", fontWeight: 600, color: "#111" }}>{job.name}</td>
                    <td style={{ padding: "12px 12px" }}>
                      <code
                        style={{
                          background: "#f3f4f6",
                          padding: "2px 8px",
                          borderRadius: 4,
                          fontSize: 12,
                          color: "#4b5563",
                        }}
                      >
                        {job.cron}
                      </code>
                    </td>
                    <td style={{ padding: "12px 12px" }}>
                      <button
                        onClick={() => handleToggleEnabled(job)}
                        style={{
                          padding: "4px 12px",
                          background: job.enabled ? "#d1fae5" : "#fee2e2",
                          color: job.enabled ? "#065f46" : "#dc2626",
                          border: "none",
                          borderRadius: 99,
                          fontSize: 12,
                          fontWeight: 600,
                          cursor: "pointer",
                        }}
                      >
                        {job.enabled ? "활성" : "비활성"}
                      </button>
                    </td>
                    <td style={{ padding: "12px 12px", color: "#6b7280", whiteSpace: "nowrap" }}>
                      {job.days}일 / {job.max_posts}개 / {job.top_celebs}명
                      {job.auto_publish && (
                        <span
                          style={{
                            marginLeft: 6,
                            fontSize: 11,
                            background: "#dbeafe",
                            color: "#1d4ed8",
                            padding: "1px 6px",
                            borderRadius: 4,
                          }}
                        >
                          자동발행
                        </span>
                      )}
                    </td>
                    <td style={{ padding: "12px 12px", color: "#9ca3af", whiteSpace: "nowrap" }}>
                      {formatDateTime(job.last_run)}
                    </td>
                    <td style={{ padding: "12px 12px", color: "#9ca3af", whiteSpace: "nowrap" }}>
                      {formatDateTime(job.next_run)}
                    </td>
                    <td style={{ padding: "12px 12px" }}>
                      <div style={{ display: "flex", gap: 6 }}>
                        <button
                          onClick={() => handleTrigger(job)}
                          disabled={triggeringId === job.id}
                          style={{
                            padding: "5px 10px",
                            background: "#ede9fe",
                            color: "#7c3aed",
                            border: "none",
                            borderRadius: 6,
                            fontSize: 12,
                            fontWeight: 600,
                            cursor: triggeringId === job.id ? "not-allowed" : "pointer",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {triggeringId === job.id ? "실행 중..." : "즉시 실행"}
                        </button>
                        <button
                          onClick={() => handleDelete(job)}
                          disabled={deletingId === job.id}
                          style={{
                            padding: "5px 10px",
                            background: "#fee2e2",
                            color: "#dc2626",
                            border: "none",
                            borderRadius: 6,
                            fontSize: 12,
                            fontWeight: 600,
                            cursor: deletingId === job.id ? "not-allowed" : "pointer",
                          }}
                        >
                          {deletingId === job.id ? "삭제 중..." : "삭제"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
