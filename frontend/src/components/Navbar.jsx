import { Link, NavLink } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { user } = useAuth();
  return (
    <header className="sticky top-0 z-30">
      <div className="mx-auto mt-4 max-w-6xl px-4">
        <div className="glass flex items-center gap-4 px-4 py-2.5">
          <Link to="/" className="flex items-center gap-2.5">
            <span className="grid h-8 w-8 place-items-center rounded-lg
                             bg-gradient-to-br from-[color:var(--color-brand)] to-[color:var(--color-brand-deep)]">
              <ShieldAlert size={17} className="text-white" />
            </span>
            <span className="font-semibold tracking-tight">
              RoadGuard <span className="text-[color:var(--color-brand)]">AI</span>
            </span>
          </Link>

          <nav className="ml-auto hidden items-center gap-1 sm:flex">
            {[["#features","Features"],["#how","How it works"],["#stats","Impact"]].map(([h,l]) => (
              <a key={h} href={h}
                 className="rounded-lg px-3 py-1.5 text-sm text-[color:var(--color-muted)] hover:bg-white/8 hover:text-[color:var(--color-ink)] transition">
                {l}
              </a>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2 sm:ml-0">
            {user ? (
              <NavLink to="/app" className="btn btn-primary">Open dashboard</NavLink>
            ) : (
              <>
                <NavLink to="/login" className="btn btn-ghost">Log in</NavLink>
                <NavLink to="/signup" className="btn btn-primary">Get started</NavLink>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
