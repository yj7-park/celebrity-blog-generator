export type Mode = "auto" | "step";

interface Props {
  mode: Mode;
  onChange: (m: Mode) => void;
}

export default function ModeToggle({ mode, onChange }: Props) {
  return (
    <div
      style={{
        display: "inline-flex",
        background: "#f3f4f6",
        borderRadius: 10,
        padding: 4,
        gap: 4,
      }}
    >
      {(["auto", "step"] as Mode[]).map((m) => (
        <button
          key={m}
          onClick={() => onChange(m)}
          style={{
            padding: "7px 18px",
            border: "none",
            borderRadius: 8,
            fontSize: 13,
            fontWeight: 600,
            cursor: "pointer",
            background: mode === m ? "#fff" : "transparent",
            color: mode === m ? "#6366f1" : "#6b7280",
            boxShadow: mode === m ? "0 1px 4px rgba(0,0,0,0.1)" : "none",
            transition: "all 0.2s",
          }}
        >
          {m === "auto" ? "🚀 일괄 실행" : "🔢 단계별 실행"}
        </button>
      ))}
    </div>
  );
}
