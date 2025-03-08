import React from "react";
import ReactDOM from "react-dom/client";
import "./App.css";
import App from "./App";
import HW from "./pages/HelloWorld/index.js";
import "./pages/HelloWorld/styles.css";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
const helloworld = ReactDOM.createRoot(document.getElementById("helloworld"));
helloworld.render(
  <React.StrictMode>
    <HW />
  </React.StrictMode>
);
