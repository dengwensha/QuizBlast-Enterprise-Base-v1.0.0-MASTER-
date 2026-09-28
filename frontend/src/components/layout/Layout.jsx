import React from "react";

export function Container({ as: Component = "div", maxWidth = 1440, style, ...props }) {
  return <Component style={{ width: "100%", maxWidth, marginInline: "auto", paddingInline: "clamp(16px, 3vw, 32px)", boxSizing: "border-box", ...style }} {...props} />;
}

export function Stack({ as: Component = "div", gap = "var(--qb-space-4)", style, ...props }) {
  return <Component style={{ display: "flex", flexDirection: "column", gap, ...style }} {...props} />;
}

export function Grid({ as: Component = "div", minColumnWidth = 240, gap = "var(--qb-space-6)", style, ...props }) {
  return <Component style={{ display: "grid", gridTemplateColumns: `repeat(auto-fit, minmax(min(100%, ${minColumnWidth}px), 1fr))`, gap, ...style }} {...props} />;
}
