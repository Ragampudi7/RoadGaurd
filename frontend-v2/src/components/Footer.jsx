import { Link } from "react-router-dom";
import { Facebook, Twitter, Linkedin, Instagram } from "lucide-react";

const productLinks = [
  { label: "Features", href: "#features" },
  { label: "How It Works", href: "#how-it-works" },
  { label: "About", href: "#about" },
  { label: "Contact", href: "#contact" },
];

export default function Footer() {
  return (
    <footer id="contact" className="border-t border-line bg-base px-6 md:px-12 pt-16 pb-8">
      <div className="mx-auto max-w-7xl">
        <div className="grid gap-12 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <div className="font-display text-xl font-bold">
              <span className="text-white">RoadGuard </span>
              <span className="text-signal">AI</span>
            </div>
            <p className="mt-3 max-w-xs text-sm text-ink/55 leading-relaxed">
              AI-powered road safety platform that detects damage, analyzes severity, and helps cities take action.
            </p>
            <div className="mt-5 flex gap-3">
              {[Facebook, Twitter, Linkedin, Instagram].map((Icon, i) => (
                <a
                  key={i}
                  href="#"
                  className="flex h-9 w-9 items-center justify-center rounded-full border border-line text-ink/60 transition-colors hover:border-signal hover:text-signal"
                >
                  <Icon className="h-4 w-4" />
                </a>
              ))}
            </div>
          </div>

          <div>
            <h4 className="font-display font-semibold text-white text-sm">Product</h4>
            <ul className="mt-4 space-y-2.5">
              {productLinks.map((l) => (
                <li key={l.label}>
                  <a href={l.href} className="text-sm text-ink/55 transition-colors hover:text-white">
                    {l.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="font-display font-semibold text-white text-sm">Account</h4>
            <p className="mt-4 text-sm text-ink/55 leading-relaxed">
              Already registered? Sign in to access your dashboard.
            </p>
            <Link to="/login" className="mt-4 inline-block text-sm font-semibold text-signal hover:underline">
              Sign in to your account {"->"}
            </Link>
          </div>
        </div>

        <div className="mt-14 border-t border-line pt-6 text-center text-xs text-ink/40">
          (c) {new Date().getFullYear()} RoadGuard AI. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
