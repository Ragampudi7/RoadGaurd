import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import AuthLayout from "../components/AuthLayout";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setBusy(true);
    await login({ email });
    setBusy(false);
    nav(loc.state?.from ?? "/app", { replace: true });
  }

  return (
    <AuthLayout
      title="Welcome back"
      sub="Sign in to file and track road reports."
      footer={<>No account? <Link to="/signup" className="font-medium text-[color:var(--color-brand)]">Create one</Link></>}>
      <form onSubmit={onSubmit} className="grid gap-4">
        <div>
          <label className="label" htmlFor="email">Email</label>
          <input id="email" className="field" type="email" required autoComplete="email"
                 placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div>
          <label className="label" htmlFor="pw">Password</label>
          <input id="pw" className="field" type="password" required
                 placeholder="Any value — nothing is checked"
                 value={pw} onChange={(e) => setPw(e.target.value)} />
        </div>
        <button className="btn btn-primary w-full" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </AuthLayout>
  );
}
