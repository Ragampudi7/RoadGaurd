import { useEffect, useState } from "react";

/**
 * True once `busy` has lasted longer than `afterMs`.
 *
 * The API runs on Render's free plan, which puts it to sleep after 15 idle
 * minutes; the first request then waits while it starts up (around a
 * minute). Rather than a spinner that looks frozen, screens use this to say
 * what is happening.
 */
export function useSlowHint(busy, afterMs = 4000) {
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    if (!busy) {
      setSlow(false);
      return undefined;
    }
    const timer = setTimeout(() => setSlow(true), afterMs);
    return () => clearTimeout(timer);
  }, [busy, afterMs]);
  return slow;
}
