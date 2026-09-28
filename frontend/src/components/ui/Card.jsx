import React from "react";
import "./foundation.css";

export default function Card({ variant = "surface", as: Component = "div", className = "", children, ...props }) {
  const modifier = variant === "surface" ? "" : `qb-card--${variant}`;
  return <Component className={["qb-card", modifier, className].filter(Boolean).join(" ")} {...props}>{children}</Component>;
}
