import { useState, useEffect } from "react";
import { getSettings, saveSettings } from "../lib/api";
import type { AppSettings } from "../lib/types";

const inputStyle: React.CSSProperties = {
  padding: "10px 14px",
  border: "1.5px solid #e5e7eb",
  borderRadius: 10,
  fontSize: 14,
  outline: "none",
  width: "100%",
  boxSizing: "border-box",
  background: "#fafafa",
  color: "#1e1b4b",
  transition: "border-color 0.15s",
};

const sectionStyle: React.CSSProperties = {
  background: "#fff",
  border: "1px solid rgba(99,102,241,0.1)",
  borderRadius: 18,
  padding: "24px 28px",
  boxShadow: "0 4px 20px rgba(30,27,75,0.07), 0 1px 4px rgba(30,27,75,0.04)",
  marginBottom: 16,
};

const DEFAULT_SETTINGS: AppSettings = {
  openai_api_key: "",
  coupang_access_key: "",
  coupang_secret_key: "",
  coupang_domain: "",
  naver_id: "",
  naver_pw: "",
  pipeline_days: 2,
  pipeline_max_posts: 10,
  pipeline_top_celebs: 3,
  chrome_user_data_dir: "",
  image_placement: "두괄식",
};

interface FieldProps {
  label: string;
  hint?: string;
  children: React.ReactNode;
}

function Field({ label, hint, children }: FieldProps) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#374151", marginBottom: 5 }}>
        {label}
      </label>
      {children}
      {hint && (
        <div style={{ fontSize: 11, color: "#9ca3af", marginTop: 4 }}>{hint}</div>
      )}
    </div>
  );
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  useEffect(() => {
    getSettings()
      .then((s) => setSettings({ ...DEFAULT_SETTINGS, ...s }))
      .catch(() => {/* 설정 없으면 기본값 사용 */})
      .finally(() => setLoading(false));
  }, []);

  const update = (key: keyof AppSettings) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const value = e.target.type === "number" ? Number(e.target.value) : e.target.value;
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    setToast(null);
    try {
      await saveSettings(settings);
      setToast({ type: "success", msg: "설정이 저장되었습니다." });
      setTimeout(() => setToast(null), 3000);
    } catch (e) {
      setToast({ type: "error", msg: `저장 실패: ${e}` });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "60px", color: "#9ca3af", fontSize: 14 }}>
        설정 불러오는 중...
      </div>
    );
  }

  return (
    <div>
      {/* 토스트 */}
      {toast && (
        <div
          style={{
            position: "fixed",
            top: 80,
            right: 24,
            zIndex: 1000,
            padding: "12px 20px",
            borderRadius: 10,
            background: toast.type === "success" ? "#d1fae5" : "#fef2f2",
            color: toast.type === "success" ? "#065f46" : "#dc2626",
            border: `1px solid ${toast.type === "success" ? "#a7f3d0" : "#fecaca"}`,
            fontSize: 14,
            fontWeight: 600,
            boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
            transition: "all 0.3s",
          }}
        >
          {toast.type === "success" ? "✅" : "⚠️"} {toast.msg}
        </div>
      )}

      {/* OpenAI */}
      <div style={sectionStyle}>
        <h2 style={{ margin: "0 0 18px", fontSize: 15, fontWeight: 700, color: "#1e1b4b", letterSpacing: "-0.01em", paddingBottom: 12, borderBottom: "1.5px solid #f3f4f6" }}>
          OpenAI 설정
        </h2>
        <Field label="OpenAI API Key" hint="블로그 글 생성에 사용됩니다.">
          <input
            type="password"
            placeholder="sk-..."
            value={settings.openai_api_key}
            onChange={update("openai_api_key")}
            style={inputStyle}
          />
        </Field>
      </div>

      {/* 쿠팡 */}
      <div style={sectionStyle}>
        <h2 style={{ margin: "0 0 18px", fontSize: 15, fontWeight: 700, color: "#1e1b4b", letterSpacing: "-0.01em", paddingBottom: 12, borderBottom: "1.5px solid #f3f4f6" }}>
          쿠팡 파트너스 설정
        </h2>
        <Field label="Access Key">
          <input
            type="text"
            placeholder="쿠팡 Access Key"
            value={settings.coupang_access_key}
            onChange={update("coupang_access_key")}
            style={inputStyle}
          />
        </Field>
        <Field label="Secret Key">
          <input
            type="password"
            placeholder="쿠팡 Secret Key"
            value={settings.coupang_secret_key}
            onChange={update("coupang_secret_key")}
            style={inputStyle}
          />
        </Field>
        <Field label="도메인" hint="쿠팡 파트너스 도메인 (예: myshop.partners.coupang.com)">
          <input
            type="text"
            placeholder="쿠팡 도메인"
            value={settings.coupang_domain}
            onChange={update("coupang_domain")}
            style={inputStyle}
          />
        </Field>
      </div>

      {/* 네이버 */}
      <div style={sectionStyle}>
        <h2 style={{ margin: "0 0 18px", fontSize: 15, fontWeight: 700, color: "#1e1b4b", letterSpacing: "-0.01em", paddingBottom: 12, borderBottom: "1.5px solid #f3f4f6" }}>
          네이버 블로그 설정
        </h2>
        <Field label="네이버 아이디">
          <input
            type="text"
            placeholder="네이버 아이디"
            value={settings.naver_id}
            onChange={update("naver_id")}
            style={inputStyle}
          />
        </Field>
        <Field label="네이버 비밀번호" hint="Selenium 자동 로그인에 사용됩니다.">
          <input
            type="password"
            placeholder="네이버 비밀번호"
            value={settings.naver_pw}
            onChange={update("naver_pw")}
            style={inputStyle}
          />
        </Field>
        <Field label="Chrome User Data 경로" hint="비워두면 프로젝트 내 chrome-user-data/ 자동 사용">
          <input
            type="text"
            placeholder="비워두면 프로젝트 내 chrome-user-data/ 자동 사용"
            value={settings.chrome_user_data_dir}
            onChange={update("chrome_user_data_dir")}
            style={inputStyle}
          />
        </Field>
      </div>

      {/* 파이프라인 기본값 */}
      <div style={sectionStyle}>
        <h2 style={{ margin: "0 0 18px", fontSize: 15, fontWeight: 700, color: "#1e1b4b", letterSpacing: "-0.01em", paddingBottom: 12, borderBottom: "1.5px solid #f3f4f6" }}>
          파이프라인 기본값
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginBottom: 12 }}>
          <Field label="수집 기간 (일)">
            <select value={settings.pipeline_days} onChange={update("pipeline_days")} style={inputStyle}>
              {[1, 2, 3, 5, 7].map((d) => <option key={d} value={d}>{d}일</option>)}
            </select>
          </Field>
          <Field label="최대 포스트 수">
            <select value={settings.pipeline_max_posts} onChange={update("pipeline_max_posts")} style={inputStyle}>
              {[5, 10, 20, 30, 50].map((n) => <option key={n} value={n}>{n}개</option>)}
            </select>
          </Field>
          <Field label="연예인 수">
            <select value={settings.pipeline_top_celebs} onChange={update("pipeline_top_celebs")} style={inputStyle}>
              {[1, 2, 3, 5].map((n) => <option key={n} value={n}>{n}명</option>)}
            </select>
          </Field>
        </div>
        <Field label="블로그 이미지 배치 방식" hint="두괄식: 이미지→텍스트 순서 / 미괄식: 텍스트→이미지 순서">
          <select value={settings.image_placement} onChange={update("image_placement")} style={inputStyle}>
            <option value="두괄식">두괄식 (이미지 먼저)</option>
            <option value="미괄식">미괄식 (텍스트 먼저)</option>
          </select>
        </Field>
      </div>

      {/* 저장 버튼 */}
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            padding: "12px 32px",
            background: saving ? "linear-gradient(90deg, #c4b5fd, #a5b4fc)" : "linear-gradient(90deg, #6366f1, #8b5cf6)",
            color: "#fff",
            border: "none",
            borderRadius: 11,
            fontSize: 15,
            fontWeight: 700,
            cursor: saving ? "not-allowed" : "pointer",
            boxShadow: saving ? "none" : "0 4px 14px rgba(99,102,241,0.4)",
            letterSpacing: "-0.01em",
          }}
        >
          {saving ? "저장 중..." : "설정 저장"}
        </button>
      </div>
    </div>
  );
}
