import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: "▦", end: true },
  { to: "/upload", label: "Upload Resumes", icon: "⬆" },
  { to: "/jobs", label: "Job Descriptions", icon: "☰" },
  { to: "/candidates", label: "Candidates", icon: "👤" },
  { to: "/screening", label: "Screening Results", icon: "★" },
  { to: "/settings", label: "Settings", icon: "⚙" },
];

interface SidebarProps {
  open: boolean;
  userEmail: string | null;
  onLogout: () => void;
}

export function Sidebar({ open, userEmail, onLogout }: SidebarProps) {
  return (
    <aside className={`sidebar${open ? " open" : ""}`} data-testid="sidebar">
      <div className="brand">
        <span className="brand-mark" aria-hidden>
          ⌕
        </span>
        Smart Resume Screener
      </div>
      <nav className="nav" aria-label="Main navigation">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              `nav-link${isActive ? " active" : ""}`
            }
          >
            <span className="nav-icon" aria-hidden>
              {item.icon}
            </span>
            {item.label}
          </NavLink>
        ))}
      </nav>
      {userEmail && (
        <div style={{ padding: "15px", borderTop: "1px solid rgba(255,255,255,0.1)", fontSize: "14px", color: "#9ca3af" }}>
          <div style={{ textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap", marginBottom: "5px" }}>
            👤 {userEmail}
          </div>
          <button
            onClick={onLogout}
            style={{
              background: "none",
              border: "none",
              color: "#f87171",
              cursor: "pointer",
              padding: "0",
              fontSize: "14px",
              textDecoration: "underline"
            }}
          >
            Sign Out
          </button>
        </div>
      )}
      <div className="sidebar-footer">v1.0 · local workspace</div>
    </aside>
  );
}

