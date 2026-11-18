import React from "react";
import "./foundation.css";

export default function Button({ variant = "primary", size = "md", fullWidth = false, loading = false, disabled = false, children, className = "", ...props }) {
  const classes = ["qb-button", `qb-button--${variant}`, size !== "md" ? `qb-button--${size}` : "", fullWidth ? "qb-button--full" : "", className].filter(Boolean).join(" ");
  return <button className={classes} disabled={disabled || loading} aria-busy={loading || undefined} {...props}>{children}</button>;
}
