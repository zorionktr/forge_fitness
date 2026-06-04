import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";

const TABS = [
  { to: "/feed", label: "Feed" },
  { to: "/chat", label: "Coach" },
  { to: "/nutrition", label: "Log" },
  { to: "/progress", label: "Progress" },
  { to: "/profile", label: "Profile" },
];

export function AppLayout() {
  const navigate = useNavigate();
  const logout = useAuth((s) => s.logout);

  const onLogout = () => {
    logout();
    navigate("/sign-in", { replace: true });
  };

  return (
    <div className="app">
      <header className="app__bar">
        <span className="app__brand">Forge</span>
        <button className="app__logout" onClick={onLogout}>
          Log out
        </button>
      </header>
      <main className="app__main">
        <Outlet />
      </main>
      <nav className="app__tabs">
        {TABS.map((t) => (
          <NavLink key={t.to} to={t.to} className={({ isActive }) => (isActive ? "tab tab--active" : "tab")}>
            {t.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
