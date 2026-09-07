import { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useReports } from "../../context/ReportsContext";
import { ShieldAlert, Save } from "lucide-react";

export default function Profile() {
  const { user, updateProfile, isMock } = useAuth();
  const { reports } = useReports();
  const [form, setForm] = useState({ name: user?.name ?? "", city: user?.city ?? "" });
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState(null);

  async function onSubmit(e) {
    e.preventDefault();
    setErr(null);
    try {
      await updateProfile(form);
      setSaved(true);
      setTimeout(() => setSaved(false), 2200);
    } catch (ex) {
      setErr(ex);
    }
  }

  return (
    <div className="grid max-w-2xl gap-5">
      <h1 className="text-2xl font-semibold tracking-tight">Profile</h1>

      <div className="glass flex items-center gap-4 p-5">
        <span className="grid h-14 w-14 place-items-center rounded-full bg-white/10 text-xl font-semibold uppercase">
          {user?.name?.[0] ?? "?"}
        </span>
        <div>
          <div className="text-lg font-semibold capitalize">{user?.name}</div>
          <div className="text-sm text-[color:var(--color-muted)]">{user?.email}</div>
          <div className="mt-1 text-xs text-[color:var(--color-muted)]">
            {reports.length} reports · joined {new Date(user?.joined ?? Date.now()).toLocaleDateString()}
          </div>
        </div>
      </div>

      <form onSubmit={onSubmit} className="glass grid gap-4 p-5">
        {err && (
          <div className="glass-soft border-[color:var(--color-danger)]/40 p-3 text-[13px] text-[color:var(--color-danger)]" role="alert">
            {err.message}
          </div>
        )}
        <div>
          <label className="label" htmlFor="pname">Display name</label>
          <input id="pname" className="field" value={form.name}
                 onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </div>
        <div>
          <label className="label" htmlFor="pcity">City</label>
          <input id="pcity" className="field" value={form.city}
                 onChange={(e) => setForm({ ...form, city: e.target.value })} />
        </div>
        <div>
          <button className="btn btn-primary"><Save size={15} /> {saved ? "Saved" : "Save changes"}</button>
        </div>
      </form>

      <div className="glass-soft flex items-start gap-2.5 p-4 text-[13px] text-[color:var(--color-muted)]">
        <ShieldAlert size={15} className={`mt-0.5 shrink-0 ${isMock ? "text-[color:var(--color-fair)]" : "text-[color:var(--color-good)]"}`} />
        {isMock ? (
          <p>
            This account is a local demo. Nothing was sent to a server, no password
            was checked, and the profile is a{" "}
            <span className="font-mono">localStorage</span> key any visitor to this
            browser can read or edit. It gates navigation, not data.
          </p>
        ) : (
          <p>
            A real account. Your password is bcrypt-hashed on the server and is
            never stored or logged in plain text. Reports are owned by this
            account and follow it to any device you sign in on.
          </p>
        )}
      </div>
    </div>
  );
}
