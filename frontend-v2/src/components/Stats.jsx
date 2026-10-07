import { useEffect, useState } from "react";
import { useInView } from "./Reveal";

const stats = [
  { value: 4, suffix: "", label: "Complaint Steps" },
  { value: 5, prefix: "<", suffix: "s", label: "AI Analysis" },
  { value: 100, suffix: "%", label: "GPS-Ready Reports" },
  { value: 24, suffix: "/7", label: "Citizen Access", noCount: true },
];

function Counter({ value, prefix = "", suffix = "", trigger }) {
  const [n, setN] = useState(0);

  useEffect(() => {
    if (!trigger) return;
    const duration = 1200;
    const start = performance.now();

    function tick(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setN(Math.round(eased * value));
      if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }, [trigger, value]);

  return (
    <span>
      {prefix}
      {n}
      {suffix}
    </span>
  );
}

export default function Stats() {
  const [ref, inView] = useInView(0.3);

  return (
    <section ref={ref} className="bg-sectionLight px-6 md:px-12 py-14 lg:py-20">
      <div className="mx-auto max-w-7xl divide-y divide-[#E4E8F0] sm:grid sm:grid-cols-4 sm:divide-y-0 sm:divide-x">
        {stats.map((s) => (
          <div key={s.label} className="py-8 sm:py-0 text-center px-4">
            <div className="font-display text-3xl sm:text-4xl font-bold text-signal">
              {s.noCount ? (
                `${s.value}${s.suffix}`
              ) : (
                <Counter value={s.value} prefix={s.prefix} suffix={s.suffix} trigger={inView} />
              )}
            </div>
            <div className="mt-2 text-sm font-medium text-mutedDark">{s.label}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
