import { useState } from "react";
import Card from "./Card";

interface Props {
  celeb: string;
  post: string;
}

export default function BlogPostPanel({ celeb, post }: Props) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(post).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <Card title={`📝 생성된 블로그 포스트 — ${celeb}`}>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 10 }}>
        <button
          onClick={handleCopy}
          style={{
            padding: "6px 14px",
            fontSize: 13,
            borderRadius: 8,
            border: "1px solid #d1d5db",
            background: copied ? "#d1fae5" : "#fff",
            cursor: "pointer",
            color: copied ? "#065f46" : "#374151",
            transition: "all 0.2s",
          }}
        >
          {copied ? "✅ 복사됨" : "📋 복사"}
        </button>
      </div>
      <pre
        style={{
          margin: 0,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          fontSize: 13.5,
          lineHeight: 1.8,
          color: "#1f2937",
          background: "#f9fafb",
          padding: 16,
          borderRadius: 8,
          maxHeight: 500,
          overflowY: "auto",
        }}
      >
        {post}
      </pre>
    </Card>
  );
}
