import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

const css = `
body { margin: 0; font-family: Arial, sans-serif; background: #fff; color: #111; }
button { padding: 6px 10px; margin-right: 6px; cursor: pointer; }
input[type="number"] { padding: 6px; width: 60px; }
pre { white-space: pre-wrap; word-wrap: break-word; background: #f5f5f5; padding: 10px; border-radius: 4px; }
.container { padding: 20px; }
h1 { margin-top: 0; }
`;

const style = document.createElement("style");
style.textContent = css;
document.head.appendChild(style);

const root = createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <div className="container">
      <App />
    </div>
  </React.StrictMode>
);