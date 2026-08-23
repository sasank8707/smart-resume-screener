import { useEffect, useState } from "react";
import {
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { ToastStack } from "./components/ToastStack";
import Dashboard from "./pages/Dashboard";
import UploadResumes from "./pages/UploadResumes";
import JobDescriptions from "./pages/JobDescriptions";
import Candidates from "./pages/Candidates";
import ScreeningResults from "./pages/ScreeningResults";
import Settings from "./pages/Settings";

const TITLES: Record<string, { title: string; sub: string }> = {
  "/": {
    title: "Dashboard",
    sub: "Overview of your resume screening activity",
  },
  "/upload": {
    title: "Upload Resumes",
    sub: "Add PDF or TXT resumes — text is extracted and parsed into structured candidate profiles",
  },
  "/jobs": {
    title: "Job Descriptions",
    sub: "Create and manage the roles you screen candidates against",
  },
  "/candidates": {
    title: "Candidates",
    sub: "Every uploaded resume with its structured extraction results",
  },
  "/screening": {
    title: "Screening Results",
    sub: "Run LLM-powered matching and review ranked, explainable results",
  },
  "/settings": {
    title: "Settings",
    sub: "System status and configuration reference",
  },
};

export default function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const meta = TITLES[location.pathname] ?? {
    title: "Smart Resume Screener",
    sub: "",
  };

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  return (
    <div className="app-shell">
      <Sidebar open={menuOpen} />
      <div className="main-area">
        <header className="topbar">
          <button
            className="menu-toggle"
            aria-label="Toggle navigation"
            onClick={() => setMenuOpen((v) => !v)}
          >
            ☰
          </button>
          <div>
            <h1>{meta.title}</h1>
            {meta.sub && <div className="topbar-sub">{meta.sub}</div>}
          </div>
          {location.pathname !== "/upload" && (
            <button
              className="btn btn-primary btn-sm"
              onClick={() => navigate("/upload")}
            >
              ⬆ Upload resumes
            </button>
          )}
        </header>
        <main className="content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/upload" element={<UploadResumes />} />
            <Route path="/jobs" element={<JobDescriptions />} />
            <Route path="/candidates" element={<Candidates />} />
            <Route path="/screening" element={<ScreeningResults />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
      <ToastStack />
    </div>
  );
}
