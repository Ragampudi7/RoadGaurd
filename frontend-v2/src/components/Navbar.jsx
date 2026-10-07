import { Link } from "react-router-dom";

export default function Navbar() {
  const links = [
    { label: "Features", href: "#features" },
    { label: "How it Works", href: "#how-it-works" },
    { label: "About", href: "#about" },
    { label: "Contact", href: "#contact" },
  ];

  return (
    <header className="absolute top-0 left-0 right-0 z-30 flex items-center justify-between px-6 md:px-12 py-6">
      <Link to="/" className="font-display text-xl font-bold tracking-tight">
        <span className="text-white">RoadGuard </span>
        <span className="text-signal">AI</span>
      </Link>

      <nav className="hidden lg:flex items-center gap-9 text-sm font-medium text-ink/80">
        {links.map(({ label, href }) => (
          <a
            key={label}
            href={href}
            className="relative transition-colors hover:text-white after:absolute after:-bottom-1.5 after:left-0 after:h-px after:w-0 after:bg-signal after:transition-all hover:after:w-full"
          >
            {label}
          </a>
        ))}
      </nav>

      <Link
        to="/signup"
        className="rounded-lg bg-signal px-5 py-2.5 text-sm font-semibold text-white shadow-glow transition-all hover:bg-signalDim"
      >
        Get Started
      </Link>
    </header>
  );
}
