import { useState, type ReactNode } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { BrandMark } from "@/features/branding/BrandMark";
import { NewPostModal } from "@/features/feed/NewPostModal";

const I = (d: string) => (
  <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d={d} />
  </svg>
);

const TABS: { to: string; label: string; icon: ReactNode }[] = [
  { to: "/feed", label: "Feed", icon: I("M3 11.5 12 4l9 7.5M5 10v10h14V10") },
  { to: "/discover", label: "Discover", icon: I("M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14ZM20 20l-4-4") },
  { to: "/chat", label: "Coach", icon: I("M4 5h16v11H8l-4 4V5Z") },
  { to: "/nutrition", label: "Log", icon: I("M5 3v8a2 2 0 0 0 2 2v8M7 3v6M16 3c-1.5 0-2 2-2 4s.5 4 2 4v8") },
  { to: "/progress", label: "Progress", icon: I("M4 19V5M4 19h16M8 16l3-4 3 2 4-6") },
  { to: "/profile", label: "Profile", icon: I("M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM5 20c1-3.5 4-5 7-5s6 1.5 7 5") },
];

export function AppLayout() {
  const [composing, setComposing] = useState(false);

  return (
    <div className="app">
      <header className="app__bar">
        <div className="app__logo">
          <BrandMark size={24} animated={false} />
          <span className="app__brand">Forge</span>
        </div>
        <button
          className="app__new"
          onClick={() => setComposing(true)}
          aria-label="New post"
          title="New post"
        >
          <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
            <path d="M12 5v14M5 12h14" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
          </svg>
        </button>
      </header>

      <main className="app__main">
        <Outlet />
      </main>

      <nav className="app__tabs">
        {TABS.map((t) => (
          <NavLink
            key={t.to}
            to={t.to}
            className={({ isActive }) => (isActive ? "tab tab--active" : "tab")}
            aria-label={t.label}
            title={t.label}
          >
            {t.icon}
          </NavLink>
        ))}
      </nav>

      {composing && <NewPostModal onClose={() => setComposing(false)} />}
    </div>
  );
}
