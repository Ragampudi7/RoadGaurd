import { FlaskConical } from "lucide-react";

/**
 * Shown wherever fabricated numbers appear. The app produces a document
 * addressed to a municipal body, so demo output has to be unmistakable.
 */
export default function DemoBadge({ className = "" }) {
  return (
    <span className={`chip demo-stripe text-[color:var(--color-fair)] border border-[color:var(--color-fair)]/40 ${className}`}>
      <FlaskConical size={12} /> Demo data
    </span>
  );
}
