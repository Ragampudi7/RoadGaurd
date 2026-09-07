import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthLayout from "../components/AuthLayout";
import { useAuth } from "../context/AuthContext";

export default function Signup() {
  const { signup, isMock } = useAuth();
  const nav = useNavigate();
  const [f, setF] = useState({ name: "", email: "", pw: "", city: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function onSubmit(e) {
    e.preventDefault();
    setBusy(true); setErr(null);
    try {
      await signup({ name: f.name, email: f.email, password: f.pw, city: f.city || undefined });
      nav("/app", { replace: true });
    } catch (ex) {
      setErr(ex);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout
      title="Create an account"
      sub="Start filing scored road reports."
      footer={<>Already have one? <Link to="/login" className="font-medium text-[color:var(--color-brand)]">Sign in</Link></>}>
      <form onSubmit={onSubmit} className="grid gap-4">
        {err && (
          <div className="glass-soft border-[color:var(--color-danger)]/40 p-3 text-[13px] text-[color:var(--color-danger)]" role="alert">
            {err.message}
          </div>
        )}
        <div>
          <label className="label" htmlFor="name">Name</label>
          <input id="name" className="field" required autoComplete="name"
                 placeholder="Siva" value={f.name} onChange={set("name")} />
        </div>
        <div>
          <label className="label" htmlFor="email2">Email</label>
          <input id="email2" className="field" type="email" required autoComplete="email"
                 placeholder="you@example.com" value={f.email} onChange={set("email")} />
        </div>
        <div>
          <label className="label" htmlFor="pw2">Password</label>
          <input id="pw2" className="field" type="password" required autoComplete="new-password"
                 minLength={isMock ? 1 : 8}
                 placeholder={isMock ? "Any value - nothing is stored" : "At least 8 characters"}
                 value={f.pw} onChange={set("pw")} />
          {!isMock && (
            <p className="mt-1 text-[11.5px] text-[color:var(--color-muted)]">
              Hashed with bcrypt before it is stored. Maximum 72 bytes.
            </p>
          )}
        </div>
        <button className="btn btn-primary w-full" disabled={busy}>
          {busy ? "Creating…" : "Create account"}
        </button>
      </form>
    </AuthLayout>
  );
}
