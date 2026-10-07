import { useState } from "react";
import { motion } from "framer-motion";
import {
  Calendar,
  ChevronDown,
  Lock,
  Mail,
  MapPin,
  Save,
  ShieldCheck,
  User,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

function ProfileSection({ id, title, description, icon: Icon, activeSection, setActiveSection, children }) {
  const open = activeSection === id;

  return (
    <section className="overflow-hidden rounded-2xl border border-line bg-panel/80 shadow-card">
      <button
        type="button"
        onClick={() => setActiveSection(open ? "" : id)}
        className="flex w-full items-center justify-between gap-4 px-5 py-5 text-left transition-colors hover:bg-panel2/60"
      >
        <span className="flex items-center gap-4">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-signal/15 text-signal">
            <Icon className="h-5 w-5" />
          </span>
          <span>
            <span className="block font-display text-lg font-semibold text-white">{title}</span>
            <span className="mt-1 block text-sm text-ink/55">{description}</span>
          </span>
        </span>
        <ChevronDown className={`h-5 w-5 shrink-0 text-muted transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          className="border-t border-line px-5 py-5"
        >
          {children}
        </motion.div>
      )}
    </section>
  );
}

export default function Profile() {
  const { user, updateProfile } = useAuth();
  const [activeSection, setActiveSection] = useState("");
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(user?.name || "");
  const [city, setCity] = useState(user?.city || "");
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const showSaved = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setError("");
    try {
      await updateProfile({ name: name.trim(), city: city.trim() });
      setEditing(false);
      showSaved();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const profileStats = [
    { label: "Role", value: user?.role === "official" ? "Municipal Official" : "Citizen", icon: ShieldCheck },
    { label: "City", value: user?.city || "Not set", icon: MapPin },
    { label: "Account", value: "Server account", icon: Calendar },
  ];

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-white lg:text-3xl">Profile</h1>
          <p className="mt-2 text-base text-ink/65">Manage your account and security settings</p>
        </div>
        {saved && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-fit rounded-xl border border-green-500/25 bg-green-500/10 px-4 py-2 text-sm text-green-300"
          >
            Changes saved successfully
          </motion.div>
        )}
      </div>

      <section className="relative overflow-hidden rounded-3xl border border-line bg-panel px-6 py-7 shadow-card lg:px-8">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(37,99,235,0.28),transparent_34%),radial-gradient(circle_at_80%_0%,rgba(34,197,94,0.12),transparent_28%)]" />
        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-5">
            <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-2xl border border-signal/30 bg-signal/15 font-display text-3xl font-bold text-signal shadow-glow">
              {user?.name?.charAt(0) || "U"}
            </div>
            <div>
              <h2 className="font-display text-3xl font-bold text-white">{user?.name}</h2>
              <p className="mt-1 text-sm text-ink/60">{user?.email}</p>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 lg:min-w-[520px]">
            {profileStats.map(({ label, value, icon: Icon }) => (
              <div key={label} className="rounded-2xl border border-white/10 bg-base/35 p-4 backdrop-blur-sm">
                <Icon className="mb-3 h-4 w-4 text-signal" />
                <p className="text-xs text-ink/45">{label}</p>
                <p className="mt-1 text-sm font-semibold text-white">{value}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="space-y-4">
        <ProfileSection
          id="account"
          title="Account Details"
          description="Open to update your name and city."
          icon={User}
          activeSection={activeSection}
          setActiveSection={setActiveSection}
        >
          <form onSubmit={handleSaveProfile} className="space-y-5">
            {error && (
              <div role="alert" className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                {error}
              </div>
            )}
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => {
                  setEditing((value) => !value);
                  setName(user?.name || "");
                  setCity(user?.city || "");
                }}
                className="rounded-xl border border-line px-4 py-2 text-sm font-medium text-ink transition hover:border-signal hover:text-signal"
              >
                {editing ? "Cancel" : "Edit"}
              </button>
            </div>

            <div className="grid gap-5 md:grid-cols-2">
              <label className="block">
                <span className="mb-2 block text-sm text-muted">Full Name</span>
                <span className="relative block">
                  <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    disabled={!editing}
                    className="input-dark pl-10 pr-4 disabled:opacity-70"
                  />
                </span>
              </label>

              <label className="block">
                <span className="mb-2 block text-sm text-muted">City</span>
                <span className="relative block">
                  <MapPin className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
                  <input
                    type="text"
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    disabled={!editing}
                    className="input-dark pl-10 pr-4 disabled:opacity-70"
                  />
                </span>
              </label>

              <label className="block md:col-span-2">
                <span className="mb-2 block text-sm text-muted">Email (sign-in identity, cannot be changed)</span>
                <span className="relative block">
                  <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
                  <input type="email" value={user?.email || ""} disabled className="input-dark pl-10 pr-4 opacity-70" />
                </span>
              </label>
            </div>

            {editing && (
              <button
                type="submit"
                disabled={busy}
                className="inline-flex items-center gap-2 rounded-xl bg-signal px-6 py-3 font-medium text-white hover:bg-signalDim disabled:opacity-60"
              >
                <Save className="h-4 w-4" />
                Save Changes
              </button>
            )}
          </form>
        </ProfileSection>

        <ProfileSection
          id="security"
          title="Security"
          description="How your account is protected."
          icon={Lock}
          activeSection={activeSection}
          setActiveSection={setActiveSection}
        >
          <ul className="space-y-2 text-sm text-ink/70">
            <li>Your password is stored only as a bcrypt hash on the server.</li>
            <li>This browser keeps a short-lived sign-in token, never the password. Logging out removes it.</li>
            <li>
              {user?.role === "official"
                ? "Official access comes from the server's allow-list and is re-checked at every login."
                : "Citizen accounts can file and withdraw complaints; only municipal officials can acknowledge or resolve them."}
            </li>
            <li className="text-ink/50">Changing a password is not available in this version.</li>
          </ul>
        </ProfileSection>
      </div>
    </div>
  );
}
