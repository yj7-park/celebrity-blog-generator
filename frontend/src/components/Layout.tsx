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
  Star,
} from "lucide-react";

const NAV_ITEMS = [
  { to: "/dashboard",  icon: LayoutDashboard, label: "대시보드" },
  { to: "/pipeline",   icon: Play,            label: "파이프라인" },
  { to: "/sources",    icon: Rss,             label: "소스 관리" },
  { to: "/coupang",    icon: ShoppingBag,     label: "쿠팡 상품" },
  { to: "/blog-writer",icon: PenLine,         label: "블로그 작성" },
  { to: "/scheduler",  icon: Clock,           label: "스케줄러" },
  { to: "/history",    icon: History,         label: "히스토리" },
  { to: "/data",       icon: Database,        label: "수집 데이터" },
  { to: "/settings",   icon: Settings,        label: "설정" },
];

const PAGE_TITLES: Record<string, string> = {
  "/dashboard":  "대시보드",
  "/pipeline":   "파이프라인",
  "/sources":    "소스 관리",
  "/coupang":    "쿠팡 상품",
  "/blog-writer":"블로그 작성",
  "/scheduler":  "스케줄러",
  "/history":    "히스토리",
  "/data":       "수집 데이터",
  "/settings":   "설정",
};

const PAGE_ICONS: Record<string, typeof LayoutDashboard> = {
  "/dashboard":  LayoutDashboard,
  "/pipeline":   Play,
  "/sources":    Rss,
  "/coupang":    ShoppingBag,
  "/blog-writer":PenLine,
  "/scheduler":  Clock,
  "/history":    History,
  "/data":       Database,
  "/settings":   Settings,
};

interface Props { children: ReactNode; }

export default function Layout({ children }: Props) {
  const [expanded, setExpanded] = useState(false);
  const location = useLocation();
  const pageTitle = PAGE_TITLES[location.pathname] ?? "셀럽 블로그 생성기";
  const PageIcon  = PAGE_ICONS[location.pathname] ?? LayoutDashboard;
  const sidebarW  = expanded ? 220 : 68;

  return (
    <div style={{
      display: "flex",
      minHeight: "100vh",
      background: "linear-gradient(135deg, #f5f3ff 0%, #eff6ff 100%)",
      fontFamily: "'Segoe UI', system-ui, -apple-system, sans-serif",
    }}>
      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      <aside
        onMouseEnter={() => setExpanded(true)}
        onMouseLeave={() => setExpanded(false)}
        style={{
          width: sidebarW,
          minHeight: "100vh",
          background: "linear-gradient(175deg, #1a1740 0%, #2a2468 60%, #1e1b4b 100%)",
          display: "flex",
          flexDirection: "column",
          transition: "width 0.22s cubic-bezier(.4,0,.2,1)",
          overflow: "hidden",
          flexShrink: 0,
          position: "fixed",
          top: 0, left: 0, bottom: 0,
          zIndex: 100,
          boxShadow: "4px 0 24px rgba(30,27,75,0.18)",
        }}
      >
        {/* Logo */}
        <div style={{
          height: 64,
          display: "flex",
          alignItems: "center",
          padding: "0 14px",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
          gap: 10,
          overflow: "hidden",
          flexShrink: 0,
        }}>
          <div style={{
            width: 36,
            height: 36,
            borderRadius: 10,
            background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
            boxShadow: "0 2px 12px rgba(99,102,241,0.45)",
          }}>
            <Star size={18} color="#fff" fill="#fff" />
          </div>
          <div style={{
            opacity: expanded ? 1 : 0,
            transform: `translateX(${expanded ? 0 : -8}px)`,
            transition: "opacity 0.18s, transform 0.18s",
            whiteSpace: "nowrap",
            overflow: "hidden",
          }}>
            <div style={{ color: "#fff", fontWeight: 800, fontSize: 14, lineHeight: 1.2 }}>셀럽 블로그</div>
            <div style={{ color: "rgba(165,180,252,0.7)", fontSize: 10, fontWeight: 500 }}>AI 생성기</div>
          </div>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: "10px 8px", display: "flex", flexDirection: "column", gap: 2 }}>
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              title={!expanded ? label : undefined}
              style={({ isActive }) => ({
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "9px 10px",
                borderRadius: 10,
                color: isActive ? "#c7d2fe" : "rgba(255,255,255,0.55)",
                background: isActive
                  ? "linear-gradient(90deg, rgba(99,102,241,0.35), rgba(99,102,241,0.15))"
                  : "transparent",
                boxShadow: isActive ? "inset 0 0 0 1px rgba(99,102,241,0.3)" : "none",
                textDecoration: "none",
                transition: "background 0.15s, color 0.15s, box-shadow 0.15s",
                overflow: "hidden",
                whiteSpace: "nowrap",
              })}
              onMouseEnter={e => {
                const el = e.currentTarget as HTMLElement;
                if (!el.style.background.includes("linear-gradient")) {
                  el.style.background = "rgba(99,102,241,0.12)";
                  el.style.color = "rgba(255,255,255,0.85)";
                }
              }}
              onMouseLeave={e => {
                const el = e.currentTarget as HTMLElement;
                if (!el.style.background.includes("linear-gradient")) {
                  el.style.background = "transparent";
                  el.style.color = "rgba(255,255,255,0.55)";
                }
              }}
            >
              <Icon size={19} style={{ flexShrink: 0 }} />
              <span style={{
                fontSize: 13,
                fontWeight: 500,
                opacity: expanded ? 1 : 0,
                transform: `translateX(${expanded ? 0 : -4}px)`,
                transition: "opacity 0.16s, transform 0.16s",
              }}>
                {label}
              </span>
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div style={{
          padding: "10px 8px",
          borderTop: "1px solid rgba(255,255,255,0.07)",
        }}>
          <div style={{
            padding: "6px 10px",
            borderRadius: 8,
            background: "rgba(255,255,255,0.04)",
            display: "flex",
            alignItems: "center",
            gap: 8,
            overflow: "hidden",
          }}>
            <div style={{
              width: 7, height: 7, borderRadius: "50%",
              background: "#4ade80",
              flexShrink: 0,
              boxShadow: "0 0 6px #4ade80",
            }} />
            <span style={{
              fontSize: 11, color: "rgba(255,255,255,0.35)", whiteSpace: "nowrap",
              opacity: expanded ? 1 : 0,
              transition: "opacity 0.16s",
            }}>v1.0.0 · 실행 중</span>
          </div>
        </div>
      </aside>

      {/* ── Main area ───────────────────────────────────────────────────── */}
      <div style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        marginLeft: sidebarW,
        transition: "margin-left 0.22s cubic-bezier(.4,0,.2,1)",
        minHeight: "100vh",
      }}>
        {/* Header */}
        <header style={{
          height: 60,
          background: "rgba(255,255,255,0.92)",
          backdropFilter: "blur(8px)",
          borderBottom: "1px solid rgba(99,102,241,0.1)",
          display: "flex",
          alignItems: "center",
          padding: "0 28px",
          position: "sticky",
          top: 0,
          zIndex: 50,
          boxShadow: "0 1px 0 rgba(99,102,241,0.08), 0 4px 16px rgba(30,27,75,0.06)",
          gap: 12,
        }}>
          <div style={{
            width: 32, height: 32,
            borderRadius: 9,
            background: "linear-gradient(135deg, rgba(99,102,241,0.12), rgba(139,92,246,0.15))",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}>
            <PageIcon size={16} color="#6366f1" />
          </div>
          <h1 style={{
            margin: 0,
            fontSize: 17,
            fontWeight: 700,
            color: "#1e1b4b",
            letterSpacing: "-0.01em",
          }}>
            {pageTitle}
          </h1>
        </header>

        {/* Content */}
        <main style={{
          flex: 1,
          padding: "28px",
          maxWidth: 1240,
          width: "100%",
          boxSizing: "border-box",
        }}>
          {children}
        </main>
      </div>
    </div>
  );
}
