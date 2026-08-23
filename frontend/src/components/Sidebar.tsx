import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: "▦", end: true },
  { to: "/upload", label: "Upload Resumes", icon: "⬆" },
  { to: "/jobs", label: "Job Descriptions", icon: "☰" },
  { to: "/candidates", label: "Candidates", icon: "👤" },
  { to: "/screening", label: "Screening Results", icon: "★" },
  { to: "/settings", label: "Settings", icon: "⚙" },
];

export function Sidebar({ open }: { open: boolean }) {
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
      <div className="sidebar-footer">v1.0 · local workspace</div>
    </aside>
  );
}
