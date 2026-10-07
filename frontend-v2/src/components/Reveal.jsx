import { useEffect, useRef, useState } from "react";

/**
 * useInView - triggers `true` once the element enters the viewport.
 * Used to drive scroll-reveal animations without a heavy animation library.
 */
export function useInView(threshold = 0.2) {
  const ref = useRef(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          observer.disconnect();
        }
      },
      { threshold }
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [threshold]);

  return [ref, inView];
}

/**
 * Reveal - wraps children and fades/slides them up into place when scrolled
 * into view. `delay` is in ms, used to stagger groups of items.
 */
export function Reveal({ children, delay = 0, className = "" }) {
  const [ref, inView] = useInView(0.15);

  return (
    <div
      ref={ref}
      className={className}
      style={{
        transitionProperty: "opacity, transform",
        transitionDuration: "700ms",
        transitionTimingFunction: "cubic-bezier(0.16, 1, 0.3, 1)",
        transitionDelay: `${delay}ms`,
        opacity: inView ? 1 : 0,
        transform: inView ? "translateY(0px)" : "translateY(28px)",
      }}
    >
      {children}
    </div>
  );
}
