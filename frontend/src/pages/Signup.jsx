import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthLayout from "../components/AuthLayout";
import { useAuth } from "../context/AuthContext";

export default function Signup() {
  const { signup } = useAuth();
  const nav = useNavigate();
  const [f, setF] = useState({ name: "", email: "", pw: "" });
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function onSubmit(e) {
    e.preventDefault();
    setBusy(true);
    await signup({ name: f.name, email: f.email });
    setBusy(false);
    nav("/app", { replace: true });
  }

  return (
    <AuthLayout
      title="Create an account"
      sub="Start filing scored road reports."
      footer={<>Already have one? <Link to="/login" className="font-medium text-[color:var(--color-brand)]">Sign in</Link></>}>
      <form onSubmit={onSubmit} className="grid gap-4">
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
          <input id="pw2" className="field" type="password" required
                 placeholder="Any value — nothing is stored server-side"
                 value={f.pw} onChange={set("pw")} />
        </div>
        <button className="btn btn-primary w-full" disabled={busy}>
          {busy ? "Creating…" : "Create account"}
        </button>
      </form>
    </AuthLayout>
  );
}
