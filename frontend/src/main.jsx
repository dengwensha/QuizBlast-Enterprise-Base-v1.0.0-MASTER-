import React from "react";
import ReactDOM from "react-dom/client";
import "./styles/tokens.css";

const root = ReactDOM.createRoot(document.getElementById("root"));
const isDraftPreview = import.meta.env.DEV && window.location.pathname === "/__visual-preview";

if (isDraftPreview) {
  import("./components/content/DraftVisualPreview.jsx").then(({ default: DraftVisualPreview }) => {
    root.render(<React.StrictMode><DraftVisualPreview /></React.StrictMode>);
  });
} else {
  import("./App.jsx").then(({ default: App }) => {
    root.render(<React.StrictMode><App /></React.StrictMode>);
  });
}
