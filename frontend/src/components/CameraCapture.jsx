import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, RotateCcw, X, Check, Loader2 } from "lucide-react";

/**
 * Take the photograph in the app instead of hunting for a file.
 *
 * This is the path the product is actually about - someone standing next to
 * the pothole - so it uses getUserMedia and a live preview rather than the
 * `capture` attribute on a file input. `capture` hands off to the phone's
 * camera app and gives you no preview, no lens choice, and nothing at all on
 * a laptop.
 *
 * Two constraints worth knowing:
 *
 * - getUserMedia needs a SECURE CONTEXT. https, or localhost. On a phone
 *   opening the dev server over http://192.168.x.x the API is simply absent,
 *   which reads as "the button is broken" unless the message says otherwise.
 * - The stream must be stopped explicitly. A component that unmounts without
 *   calling stop() leaves the camera light on, which users notice and rightly
 *   dislike.
 */
export default function CameraCapture({ onCapture, onClose }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [error, setError] = useState(null);
  const [ready, setReady] = useState(false);
  const [shot, setShot] = useState(null);          // { blob, url }
  const [facing, setFacing] = useState("environment");
  const [hasMultiple, setHasMultiple] = useState(false);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  const start = useCallback(async (mode) => {
    setError(null);
    setReady(false);
    stop();

    if (!navigator.mediaDevices?.getUserMedia) {
      setError(
        window.isSecureContext
          ? "This browser does not support camera capture. Choose a file instead."
          : "The camera needs a secure connection (https, or localhost). " +
            "On a phone over plain http the browser hides the camera entirely — " +
            "choose a file instead."
      );
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: mode }, width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {});
      }
      setReady(true);

      // Only offer the flip control when there is something to flip to.
      // enumerateDevices only labels cameras after permission is granted,
      // which is why this runs here and not before.
      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        setHasMultiple(devices.filter((d) => d.kind === "videoinput").length > 1);
      } catch { /* not fatal */ }
    } catch (e) {
      setError(
        e.name === "NotAllowedError"
          ? "Camera permission was denied. Allow it in the browser's address bar, or choose a file instead."
          : e.name === "NotFoundError"
            ? "No camera found on this device. Choose a file instead."
            : `Could not open the camera (${e.name}). Choose a file instead.`
      );
    }
  }, [stop]);

  useEffect(() => {
    start(facing);
    return stop;
  }, [facing, start, stop]);

  // Revoke the preview URL when it is replaced or the component goes away,
  // otherwise every retake leaks a blob for the life of the page.
  useEffect(() => () => { if (shot?.url) URL.revokeObjectURL(shot.url); }, [shot]);

  function take() {
    const video = videoRef.current;
    // A frame with no dimensions yet produces an empty canvas and a silent
    // no-op. Say so instead of appearing to ignore the button.
    if (!video || !video.videoWidth || !video.videoHeight) {
      setError("The camera is not ready yet — give it a moment and try again.");
      return;
    }
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    // 0.92 keeps the compression artefacts well clear of the crack widths the
    // model has to see. The backend's limit is 10 MB; a 1080p frame at this
    // quality is a few hundred KB.
    canvas.toBlob(
      (blob) => blob && setShot({ blob, url: URL.createObjectURL(blob) }),
      "image/jpeg",
      0.92
    );
  }

  function use() {
    if (!shot) return;
    const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
    onCapture(new File([shot.blob], `road-${stamp}.jpg`, { type: "image/jpeg" }));
    stop();
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/75 p-4 backdrop-blur-sm"
         role="dialog" aria-modal="true" aria-label="Take a photograph">
      <div className="glass w-full max-w-2xl overflow-hidden p-4">
        <div className="mb-3 flex items-center gap-3">
          <h2 className="font-semibold">Take a photograph</h2>
          <button type="button" onClick={() => { stop(); onClose(); }}
                  aria-label="Close camera"
                  className="ml-auto rounded-lg p-2 hover:bg-white/10 cursor-pointer">
            <X size={17} />
          </button>
        </div>

        <div className="relative aspect-video overflow-hidden rounded-xl bg-black">
          {/* The video stays mounted and the still overlays it. Swapping the
              two would mount a NEW video element with no srcObject, so after a
              Retake the preview is black and the next Capture reads a
              zero-width frame and silently does nothing. */}
          <video ref={videoRef} playsInline muted
                 className="h-full w-full object-cover" />
          {shot && (
            <img src={shot.url} alt="Captured road surface"
                 className="absolute inset-0 h-full w-full bg-black object-contain" />
          )}
          {!ready && !error && !shot && (
            <div className="absolute inset-0 grid place-items-center text-sm text-white/70">
              <span className="inline-flex items-center gap-2">
                <Loader2 size={16} className="animate-spin" /> Starting the camera…
              </span>
            </div>
          )}
        </div>

        {error && (
          <div className="glass-soft mt-3 border-[color:var(--color-danger)]/40 p-3 text-[13px] text-[color:var(--color-danger)]"
               role="alert">
            {error}
          </div>
        )}

        <div className="mt-4 flex flex-wrap gap-2">
          {shot ? (
            <>
              <button type="button" className="btn btn-primary" onClick={use}>
                <Check size={16} /> Use this photo
              </button>
              <button type="button" className="btn btn-ghost"
                      onClick={() => { URL.revokeObjectURL(shot.url); setShot(null); }}>
                <RotateCcw size={15} /> Retake
              </button>
            </>
          ) : (
            <>
              <button type="button" className="btn btn-primary" disabled={!ready} onClick={take}>
                <Camera size={16} /> Capture
              </button>
              {hasMultiple && (
                <button type="button" className="btn btn-ghost"
                        onClick={() => setFacing((f) => (f === "environment" ? "user" : "environment"))}>
                  <RotateCcw size={15} /> Flip camera
                </button>
              )}
            </>
          )}
          <button type="button" className="btn btn-ghost ml-auto"
                  onClick={() => { stop(); onClose(); }}>
            Cancel
          </button>
        </div>

        <p className="mt-3 text-xs leading-relaxed text-[color:var(--color-muted)]">
          Frame the defect so the surrounding road is visible — severity is
          judged by how much of the frame the damage covers, so a photo taken
          from directly above a pothole makes it look worse than it is.
        </p>
      </div>
    </div>
  );
}
