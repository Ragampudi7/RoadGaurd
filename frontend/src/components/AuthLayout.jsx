import { Link } from "react-router-dom";
import { USE_MOCK } from "../lib/api";
import { ShieldAlert } from "lucide-react";

export default function AuthLayout({ title, sub, children, footer }) {
  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* photo side — a real road from the training set */}
      <div className="relative hidden lg:block">
        <img src="/img/hero-alt.webp" alt=""
             className="absolute inset-0 h-full w-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0a0d12] via-[#0a0d12]/55 to-transparent" />
        <div className="absolute bottom-0 p-10">
          <div className="glass max-w-md p-6">
            <p className="text-lg font-medium leading-snug">
              Photograph a defect. Get a scored, complaint-ready report your
              municipal body can act on.
            </p>
            <p className="mt-3 text-sm text-[color:var(--color-muted)]">
              Detection model trained on 3,224 road images — 0.796 mAP50 on held-out data.
            </p>
          </div>
        </div>
      </div>

      {/* form side */}
      <div className="flex flex-col justify-center px-5 py-12 sm:px-12">
        <div className="mx-auto w-full max-w-sm">
          <Link to="/" className="mb-8 inline-flex items-center gap-2.5">
            <span className="grid h-9 w-9 place-items-center rounded-lg
                             bg-gradient-to-br from-[color:var(--color-brand)] to-[color:var(--color-brand-deep)]">
              <ShieldAlert size={18} className="text-white" />
            </span>
            <span className="font-semibold tracking-tight">
              RoadGuard <span className="text-[color:var(--color-brand)]">AI</span>
            </span>
          </Link>

          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          <p className="mt-1.5 mb-7 text-sm text-[color:var(--color-muted)]">{sub}</p>

          {children}

          {footer && <div className="mt-6 text-sm text-[color:var(--color-muted)]">{footer}</div>}

          <p className="mt-8 text-[11.5px] leading-relaxed text-[color:var(--color-muted)]">
            {USE_MOCK
              ? "Demo sign-in: no password is checked and nothing reaches a server. The profile is a key in this browser, so it gates navigation, not data."
              : "Passwords are hashed with bcrypt and never stored or logged in plain text. Your session is a signed token held in this browser."}
          </p>
        </div>
      </div>
    </div>
  );
}
