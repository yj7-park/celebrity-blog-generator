import { useState, ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Play,
  ShoppingBag,
  PenLine,
  Clock,
  History,
  Database,
  Rss,
  Settings,
} from "lucide-react";

const NAV_ITEMS = [
  { to: "/dashboard", icon: LayoutDashboard, label: "대시보드" },
  { to: "/pipeline", icon: Play, label: "파이프라인" },
  { to: "/sources", icon: Rss, label: "소스 관리" },
  { to: "/coupang", icon: ShoppingBag, label: "쿠팡 상품" },
  { to: "/blog-writer", icon: PenLine, label: "블로그 작성" },
  { to: "/scheduler", icon: Clock, label: "스케줄러" },
  { to: "/history", icon: History, label: "히스토리" },
  { to: "/data", icon: Database, label: "수집 데이터" },
  { to: "/settings", icon: Settings, label: "설정" },
];

const PAGE_TITLES: Record<string, string> = {
  "/dashboard": "대시보드",
  "/pipeline": "파이프라인",
  "/sources": "소스 관리",
  "/coupang": "쿠팡 상품",
  "/blog-writer": "블로그 작성",
  "/scheduler": "스케줄러",
  "/history": "히스토리",
  "/data": "수집 데이터",
  "/settings": "설정",
};

interface Props {
  children: ReactNode;
}

export default function Layout({ children }: Props) {
  const [hovered, setHovered] = useState(false);
  const location = useLocation();
  const pageTitle = PAGE_TITLES[location.pathname] ?? "셀럽 블로그 생성기";
  const sidebarWidth = hovered ? 240 : 64;

  return (
    <div
      style={{
        display: "flex",
        minHeight: "100vh",
        background: "#f5f3ff",
        fontFamily: "'Segoe UI', system-ui, sans-serif",
      }}
    >
      {/* Sidebar */}
      <div
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        style={{
          width: sidebarWidth,
          minHeight: "100vh",
          background: "#1e1b4b",
          display: "flex",
          flexDirection: "column",
          transition: "width 0.25s ease",
          overflow: "hidden",
          flexShrink: 0,
          position: "fixed",
          top: 0,
          left: 0,
          bottom: 0,
          zIndex: 100,
        }}
      >
        {/* Logo */}
        <div
          style={{
            height: 64,
            display: "flex",
            alignItems: "center",
            padding: "0 16px",
            borderBottom: "1px solid rgba(255,255,255,0.1)",
            gap: 12,
            overflow: "hidden",
            flexShrink: 0,
          }}
        >
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
              fontSize: 16,
            }}
          >
            ★
          </div>
          {hovered && (
            <span
              style={{
                color: "#fff",
                fontWeight: 700,
                fontSize: 14,
                whiteSpace: "nowrap",
                overflow: "hidden",
              }}
            >
              셀럽 블로그
            </span>
          )}
        </div>

        {/* Nav Items */}
        <nav style={{ flex: 1, padding: "12px 0" }}>
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              style={({ isActive }) => ({
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "12px 16px",
                color: isActive ? "#a5b4fc" : "rgba(255,255,255,0.65)",
                background: isActive ? "rgba(99,102,241,0.2)" : "transparent",
                borderLeft: isActive ? "3px solid #6366f1" : "3px solid transparent",
                textDecoration: "none",
                transition: "all 0.15s",
                overflow: "hidden",
                whiteSpace: "nowrap",
              })}
            >
              <Icon size={20} style={{ flexShrink: 0 }} />
              {hovered && (
                <span style={{ fontSize: 14, fontWeight: 500 }}>{label}</span>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Version */}
        {hovered && (
          <div
            style={{
              padding: "12px 16px",
              fontSize: 11,
              color: "rgba(255,255,255,0.3)",
              borderTop: "1px solid rgba(255,255,255,0.1)",
            }}
          >
            v1.0.0
          </div>
        )}
      </div>

      {/* Main */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          marginLeft: sidebarWidth,
          transition: "margin-left 0.25s ease",
          minHeight: "100vh",
        }}
      >
        {/* Header */}
        <header
          style={{
            height: 64,
            background: "#fff",
            borderBottom: "1px solid #e5e7eb",
            display: "flex",
            alignItems: "center",
            padding: "0 28px",
            position: "sticky",
            top: 0,
            zIndex: 50,
            boxShadow: "0 1px 4px rgba(0,0,0,0.04)",
          }}
        >
          <h1
            style={{
              margin: 0,
              fontSize: 18,
              fontWeight: 700,
              color: "#1e1b4b",
            }}
          >
            {pageTitle}
          </h1>
        </header>

        {/* Content */}
        <main
          style={{
            flex: 1,
            padding: "28px",
            maxWidth: 1200,
            width: "100%",
            boxSizing: "border-box",
          }}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
