import React from "react";
import "./foundation.css";

const symbols = { info: "ℹ", success: "✓", warning: "!", error: "!" };

export default function Alert({ variant = "info", title, children, className = "", ...props }) {
  return <div role={variant === "error" ? "alert" : "status"} className={["qb-alert", `qb-alert--${variant}`, className].filter(Boolean).join(" ")} {...props}>
    <span aria-hidden="true">{symbols[variant] || symbols.info}</span>
    <div>{title && <strong>{title}</strong>}{children && <div>{children}</div>}</div>
  </div>;
}
