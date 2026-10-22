// Shared helpers + reusable layout used by every page
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
document.documentElement.dataset.theme = localStorage.getItem("mv_theme") || "light";   // saved theme
function toast(msg, err) {
  let box = $("#toast") || document.body.appendChild(Object.assign(document.createElement("div"), {id: "toast"}));
  const d = document.createElement("div"); d.textContent = msg; if (err) d.className = "e";
  box.appendChild(d); setTimeout(() => d.remove(), 3500);
}
async function api(path, opts = {}) {            // REST helper: adds the login token, shows readable errors
  opts.headers = Object.assign({}, opts.headers, {Authorization: "Bearer " + (localStorage.getItem("mv_token") || "")});
  const r = await fetch("/api" + path, opts), j = await r.json().catch(() => ({}));
  if (r.status === 401 && !path.startsWith("/login")) { localStorage.removeItem("mv_token"); location.href = "login.html"; }
  if (!r.ok) throw new Error(j.error || "Server error"); return j;
}
const jsend = (p, b, m = "POST") => api(p, {method: m, headers: {"Content-Type": "application/json"}, body: JSON.stringify(b)});
function requireLogin() { if (!localStorage.getItem("mv_token")) location.href = "login.html"; }
const PAGES = [["dashboard","Dashboard"],["upload","Upload"],["classification","Classification"],["explainable-ai","Explainable AI"],["report","Report"],["history","Scan History"],["patients","Patients"],["gallery","Gallery"],["analytics","Analytics"],["model-insights","Model Insights"],["profile","Profile & Settings"],["support","Help & Support"]];
function navbar(active) {                        // sidebar for logged-in pages (becomes a drawer on mobile)
  requireLogin(); document.body.classList.add("app"); active = active.replace(".html", "");
  document.body.insertAdjacentHTML("afterbegin",
    `<div class="topbar"><button onclick="document.querySelector('.side').classList.toggle('open')" aria-label="Menu">☰</button><b>MediVision AI</b></div>
     <aside class="side"><a class="logo" href="index.html">Medi<b>Vision</b> AI</a>` +
    PAGES.map(([h, t]) => `<a class="l ${h === active ? "on" : ""}" href="${h}.html${["classification","explainable-ai","report"].includes(h) ? location.search : ""}">${t}</a>`).join("") +
    `<a class="l" href="#" onclick="localStorage.removeItem('mv_token');location.href='login.html'">Logout</a></aside>`);
}
function pubnav() {                              // top bar for public pages
  document.body.insertAdjacentHTML("afterbegin", `<nav><a class="logo" href="index.html">Medi<b>Vision</b> AI</a><div class="links"><a class="l" href="index.html">Home</a><a class="l" href="login.html">Login</a><a class="l" href="signup.html">Sign up</a></div></nav>`);
}
const scanId = () => new URLSearchParams(location.search).get("id");
const loadScan = () => scanId() ? api("/scans/" + scanId()) : Promise.resolve(null);
const demoBanner = d => d.mode === "demo" ? '<div class="demo">DEMO MODE: no trained model is connected. These values are sample numbers, NOT a real prediction.</div>' : "";
const charts = {};
function chart(id, cfg) { if (charts[id]) charts[id].destroy(); charts[id] = new Chart(document.getElementById(id), cfg); }
function modal(id, open) { document.getElementById(id).classList.toggle("open", open); }
const COLORS = ["#42D9E8", "#A78BFA", "#36CFC9", "#17233D", "#f59e0b"];
