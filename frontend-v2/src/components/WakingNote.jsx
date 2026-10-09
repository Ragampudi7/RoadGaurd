import { Coffee } from "lucide-react";

/** Shown when a request is taking long because the free server is waking up. */
export default function WakingNote({ children }) {
  return (
    <div
      role="status"
      data-testid="waking-note"
      className="flex items-start gap-2 rounded-lg border border-signal/30 bg-signal/10 px-4 py-3 text-sm text-ink/80"
    >
      <Coffee className="mt-0.5 h-4 w-4 shrink-0 text-signal" />
      <span>
        {children ||
          "The server is waking up - free hosting puts it to sleep when nobody has used it for a while. This can take up to a minute; please keep this page open."}
      </span>
    </div>
  );
}
