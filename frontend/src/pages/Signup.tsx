import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";

interface SignupProps {
  onSignupSuccess: () => void;
}

export default function Signup({ onSignupSuccess }: SignupProps) {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api.register({ email, password });
      // Log in automatically after registration
      const loginResp = await api.login({ email, password });
      localStorage.setItem("token", loginResp.access_token);
      onSignupSuccess();
      navigate("/");
    } catch (err: any) {
      setError(err.message || "Registration failed. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: "400px", margin: "100px auto", padding: "0 20px" }}>
      <div className="card card-pad">
        <h2 className="section-title">Sign Up</h2>
        <p className="section-hint">Create a new private account to manage and screen candidates.</p>
        
        {error && (
          <div style={{ backgroundColor: "#fee2e2", color: "#b91c1c", padding: "10px", borderRadius: "6px", marginBottom: "15px", fontSize: "14px" }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "15px" }}>
            <label style={{ display: "block", marginBottom: "5px", fontSize: "14px", fontWeight: 500 }}>Email Address</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={{ width: "100%", padding: "8px 12px", border: "1px solid #d1d5db", borderRadius: "6px", fontSize: "14px" }}
            />
          </div>

          <div style={{ marginBottom: "20px" }}>
            <label style={{ display: "block", marginBottom: "5px", fontSize: "14px", fontWeight: 500 }}>Password (min 6 chars)</label>
            <input
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={{ width: "100%", padding: "8px 12px", border: "1px solid #d1d5db", borderRadius: "6px", fontSize: "14px" }}
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
            style={{ width: "100%", padding: "10px" }}
          >
            {loading ? "Creating account..." : "Sign Up"}
          </button>
        </form>

        <div style={{ marginTop: "20px", textAlign: "center", fontSize: "14px" }}>
          Already have an account? <Link to="/login" style={{ color: "#2563eb", textDecoration: "underline" }}>Sign In</Link>
        </div>
      </div>
    </div>
  );
}
