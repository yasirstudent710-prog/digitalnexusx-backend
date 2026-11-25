// DigitalNexusX — website-integration.js
// Paste / adapt this in digitalnexusx.com frontend. Change API_BASE after deployment.
const API_BASE = "https://YOUR-BACKEND.up.railway.app"; // e.g. Railway URL, or http://127.0.0.1:8000 locally

// 1) Contact form -> POST /api/leads
// Give your form id="contactForm" and inputs name="name|phone|email|service|message"
document.getElementById("contactForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(e.target).entries());
  const res = await fetch(`${API_BASE}/api/leads`, {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data)
  });
  alert(res.ok ? "Thank you! We reply within 24 hours." : "Something went wrong, please WhatsApp us.");
  if (res.ok) e.target.reset();
});

// 2) Homepage stats -> GET /api/stats (replaces 0+ / 0.0x placeholders)
// Add ids: statLeads, statSales, statCPL, statRoas in your homepage HTML
fetch(`${API_BASE}/api/stats`).then(r => r.json()).then(s => {
  if (document.getElementById("statLeads")) document.getElementById("statLeads").textContent = s.leads_generated + "+";
  if (document.getElementById("statSales")) document.getElementById("statSales").textContent = s.sales_delivered + "+";
  if (document.getElementById("statCPL")) document.getElementById("statCPL").textContent = "PKR " + s.cost_per_lead;
  if (document.getElementById("statRoas")) document.getElementById("statRoas").textContent = s.roas + "x";
}).catch(()=>{});
