import React from "react";
import "./foundation.css";

export default function Input({ label, error, supportingText, id, className = "", ...props }) {
  const support = error || supportingText;
  const supportId = support && id ? `${id}-support` : undefined;
  return <label className="qb-field" htmlFor={id}>
    {label && <span className="qb-field__label">{label}</span>}
    <input id={id} className={["qb-input", error ? "qb-input--error" : "", className].filter(Boolean).join(" ")} aria-invalid={error ? true : undefined} aria-describedby={supportId} {...props} />
    {support && <span id={supportId} className={`qb-field__support${error ? " qb-field__support--error" : ""}`}>{support}</span>}
  </label>;
}
