import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import "./stage-viewport.css";

export default function StageViewport({ enabled, header, children }) {
  const rootRef = useRef(null);
  const viewportRef = useRef(null);
  const contentRef = useRef(null);
  const [fit, setFit] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [error, setError] = useState("");
  const [metrics, setMetrics] = useState({ width: 0, naturalWidth: 0, height: 0, scale: 1 });
  const fullscreenSupported = Boolean(document.fullscreenEnabled && document.documentElement.requestFullscreen);

  useEffect(() => {
    if (!enabled) return;
    const root = rootRef.current;
    const update = () => setFullscreen(document.fullscreenElement === root);
    document.addEventListener("fullscreenchange", update);
    return () => {
      document.removeEventListener("fullscreenchange", update);
      if (document.fullscreenElement === root) document.exitFullscreen().catch(() => {});
    };
  }, [enabled]);

  useLayoutEffect(() => {
    if (!enabled || !fit) return;
    let disposed = false;
    let frame;
    const measure = () => {
      if (disposed) return;
      const viewport = viewportRef.current;
      const content = contentRef.current;
      const width = viewport.clientWidth;
      const availableHeight = viewport.clientHeight;
      const naturalWidth = Math.max(width, content.scrollWidth);
      const height = content.scrollHeight;
      if (!width || !availableHeight || !height) return;
      // Round down so fractional CSS pixels never crop the last row.
      const scale = Math.floor(Math.min(1, width / naturalWidth, availableHeight / height) * 10000) / 10000;
      setMetrics(current => current.width === width && current.naturalWidth === naturalWidth &&
        current.height === height && current.scale === scale ? current : { width, naturalWidth, height, scale });
    };
    const schedule = () => {
      if (disposed) return;
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(measure);
    };
    const observer = new ResizeObserver(schedule);
    const contentElement = contentRef.current;
    observer.observe(viewportRef.current);
    observer.observe(contentElement);
    // Text can change scroll width without changing the content's border box.
    const mutations = new MutationObserver(schedule);
    mutations.observe(contentElement, { subtree: true, childList: true, characterData: true });
    contentElement.addEventListener("animationend", schedule);
    contentElement.addEventListener("transitionend", schedule);
    window.addEventListener("resize", schedule);
    document.fonts?.ready.then(schedule);
    measure();
    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      observer.disconnect();
      mutations.disconnect();
      contentElement.removeEventListener("animationend", schedule);
      contentElement.removeEventListener("transitionend", schedule);
      window.removeEventListener("resize", schedule);
    };
  }, [enabled, fit]);

  const toggleFullscreen = async () => {
    setError("");
    try {
      if (document.fullscreenElement === rootRef.current) await document.exitFullscreen();
      else await rootRef.current.requestFullscreen();
    } catch {
      setError("Tam ekran açılamadı. Tarayıcı iznini kontrol ederek tekrar deneyin.");
    }
  };

  if (!enabled) return <>{header}{children}</>;

  return (
    <div ref={rootRef} className={`qb-stage${fit ? " qb-stage--fit" : ""}`}>
      <div className="qb-stage__toolbar" role="group" aria-label="Ekran görünümü">
        <button type="button" aria-pressed={fit} onClick={() => setFit(current => !current)}>
          {fit ? "Normal görünüm" : "Ekrana sığdır"}
        </button>
        <button type="button" aria-pressed={fullscreen} disabled={!fullscreenSupported}
          title={fullscreenSupported ? undefined : "Bu tarayıcı tam ekranı desteklemiyor."}
          onClick={toggleFullscreen}>
          {fullscreen ? "Tam ekrandan çık" : "Tam ekran"}
        </button>
        {error && <span role="status">{error}</span>}
      </div>
      {header}
      <div ref={viewportRef} className="qb-stage__viewport">
        <div className="qb-stage__frame" style={fit ? {
          width: metrics.naturalWidth * metrics.scale,
          height: metrics.height * metrics.scale,
        } : undefined}>
          <div ref={contentRef} className="qb-stage__content" style={fit ? {
            width: metrics.width || "100%",
            transform: `scale(${metrics.scale})`,
          } : undefined}>
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
