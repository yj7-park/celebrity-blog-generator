import { useState } from "react";
import AutoMode from "./components/AutoMode";
import ModeToggle, { type Mode } from "./components/ModeToggle";
import StepMode from "./components/StepMode";

export default function App() {
  const [apiKey, setApiKey] = useState("");
  const [days, setDays] = useState(2);
  const [mode, setMode] = useState<Mode>("auto");

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
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <h1 style={{ margin: "0 0 6px", fontSize: 28, fontWeight: 700, color: "#1e1b4b" }}>
            🌟 셀럽 아이템 블로그 생성기
          </h1>
          <p style={{ margin: 0, color: "#6b7280", fontSize: 14 }}>
            네이버 블로그에서 트렌딩 연예인 아이템을 수집하고 블로그 포스트를 자동 생성합니다.
          </p>
        </div>

        {/* Config panel */}
        <div
          style={{
            background: "#fff",
            border: "1px solid #e5e7eb",
            borderRadius: 16,
            padding: "20px 24px",
            marginBottom: 20,
            boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
          }}
        >
          <div style={{ display: "grid", gridTemplateColumns: "1fr auto auto", gap: 10, alignItems: "center" }}>
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
                boxSizing: "border-box",
              }}
            />
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              style={{
                padding: "10px 12px",
                border: "1px solid #d1d5db",
                borderRadius: 10,
                fontSize: 14,
                background: "#fff",
                cursor: "pointer",
              }}
            >
              {[1, 2, 3, 5, 7].map((d) => (
                <option key={d} value={d}>최근 {d}일</option>
              ))}
            </select>
            <ModeToggle mode={mode} onChange={setMode} />
          </div>
        </div>

        {/* Mode content */}
        {mode === "auto"
          ? <AutoMode apiKey={apiKey} days={days} />
          : <StepMode apiKey={apiKey} days={days} />
        }
      </div>
    </div>
  );
}
