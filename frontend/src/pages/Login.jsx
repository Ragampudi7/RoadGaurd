import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import AuthLayout from "../components/AuthLayout";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login, isMock } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  async function onSubmit(e) {
    e.preventDefault();
    setBusy(true); setErr(null);
    try {
      await login({ email, password: pw });
      nav(loc.state?.from ?? "/app", { replace: true });
    } catch (ex) {
      setErr(ex);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout
      title="Welcome back"
      sub="Sign in to file and track road reports."
      footer={<>No account? <Link to="/signup" className="font-medium text-[color:var(--color-brand)]">Create one</Link></>}>
      <form onSubmit={onSubmit} className="grid gap-4">
        {err && (
          <div className="glass-soft border-[color:var(--color-danger)]/40 p-3 text-[13px] text-[color:var(--color-danger)]" role="alert">
            {err.message}
          </div>
        )}
        <div>
          <label className="label" htmlFor="email">Email</label>
          <input id="email" className="field" type="email" required autoComplete="email"
                 placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div>
          <label className="label" htmlFor="pw">Password</label>
          <input id="pw" className="field" type="password" required autoComplete="current-password"
                 placeholder={isMock ? "Any value - nothing is checked" : "Your password"}
                 value={pw} onChange={(e) => setPw(e.target.value)} />
        </div>
        <button className="btn btn-primary w-full" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </AuthLayout>
  );
}
