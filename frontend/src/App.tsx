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
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import { api } from "./api/client";

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
  const [user, setUser] = useState<{ email: string } | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  const fetchUser = async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      setUser(null);
      setAuthChecked(true);
      return;
    }
    try {
      const u = await api.me();
      setUser(u);
    } catch {
      localStorage.removeItem("token");
      setUser(null);
    } finally {
      setAuthChecked(true);
    }
  };

  useEffect(() => {
    fetchUser();
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("token");
    setUser(null);
    navigate("/login");
  };

  const meta = TITLES[location.pathname] ?? {
    title: "Smart Resume Screener",
    sub: "",
  };

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  if (!authChecked) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
        Loading session...
      </div>
    );
  }

  if (!user) {
    return (
      <>
        <Routes>
          <Route path="/login" element={<Login onLoginSuccess={fetchUser} />} />
          <Route path="/signup" element={<Signup onSignupSuccess={fetchUser} />} />
          <Route path="*" element={<Login onLoginSuccess={fetchUser} />} />
        </Routes>
        <ToastStack />
      </>
    );
  }

  return (
    <div className="app-shell">
      <Sidebar open={menuOpen} userEmail={user.email} onLogout={handleLogout} />
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
            <Route path="*" element={<Dashboard />} />
          </Routes>
        </main>
      </div>
      <ToastStack />
    </div>
  );
}

