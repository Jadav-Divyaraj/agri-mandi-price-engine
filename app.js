/* =============================================
   AGROREACH INDIA — app.js
   Bootstrap carousel handles the hero slideshow.
   This file handles: nav, counters, prices,
   product card updates, modal, enquiry form.
   ============================================= */


// ---- MANDI PRICE DATA (mock — replace with API) ----
// When your backend is ready, fetch this from /api/prices
const mandiPrices = [
  { product: "cumin",       name: "Cumin Seeds",    category: "Spices",     price: 28400, unit: "quintal", prev: 27900 },
  { product: "turmeric",    name: "Turmeric",       category: "Spices",     price: 14200, unit: "quintal", prev: 14600 },
  { product: "chilli",      name: "Red Chilli",     category: "Spices",     price: 17800, unit: "quintal", prev: 17500 },
  { product: "mango",       name: "Alphonso Mango", category: "Fruits",     price: 32000, unit: "quintal", prev: 31000 },
  { product: "pomegranate", name: "Pomegranate",    category: "Fruits",     price: 9800,  unit: "quintal", prev: 10200 },
  { product: "grapes",      name: "Grapes",         category: "Fruits",     price: 6400,  unit: "quintal", prev: 6200  },
  { product: "onion",       name: "Onion",          category: "Vegetables", price: 1850,  unit: "quintal", prev: 2100  },
  { product: "potato",      name: "Potato",         category: "Vegetables", price: 1200,  unit: "quintal", prev: 1150  },
  { product: "tomato",      name: "Tomato",         category: "Vegetables", price: 2400,  unit: "quintal", prev: 2600  },
  { product: "basmati",     name: "Basmati Rice",   category: "Grains",     price: 6800,  unit: "quintal", prev: 6500  },
  { product: "wheat",       name: "Wheat",          category: "Grains",     price: 2280,  unit: "quintal", prev: 2280  },
  { product: "cashew",      name: "Cashew W320",    category: "Dry Fruits", price: 88000, unit: "quintal", prev: 86000 },
];

// Simulate small live fluctuations (± 0.5%) every 15s
function simulateLiveFluctuation() {
  mandiPrices.forEach(p => {
    p.prev  = p.price;
    const delta = Math.floor(p.price * (Math.random() * 0.01 - 0.005));
    p.price = Math.max(100, p.price + delta);
  });
  renderPriceTable();
  updateCardPrices();
  renderTicker();
  updateLastUpdated();
}

// ---- NAVBAR ----
const navbar = document.getElementById("navbar");
window.addEventListener("scroll", () => {
  navbar.classList.toggle("scrolled", window.scrollY > 30);
});

// Mobile menu — animated drawer with X button and backdrop
const hamburger   = document.getElementById("hamburger");
const mobileMenu  = document.getElementById("mobileMenu");
const mobBackdrop = document.getElementById("mobBackdrop");

function openMobileMenu() {
  mobileMenu.classList.add("open");
  mobBackdrop.classList.add("show");
  hamburger.classList.add("open");
  hamburger.setAttribute("aria-expanded", "true");
  document.body.style.overflow = "hidden";
}
function closeMobileMenu() {
  mobileMenu.classList.remove("open");
  mobBackdrop.classList.remove("show");
  hamburger.classList.remove("open");
  hamburger.setAttribute("aria-expanded", "false");
  document.body.style.overflow = "";
}
hamburger.addEventListener("click", () => {
  mobileMenu.classList.contains("open") ? closeMobileMenu() : openMobileMenu();
});
// Close on Escape key
document.addEventListener("keydown", e => { if (e.key === "Escape") closeMobileMenu(); });
window.closeMobileMenu = closeMobileMenu;

// ---- COUNTER ANIMATION ----
function animateCounters() {
  document.querySelectorAll(".stat-num").forEach(el => {
    const target = parseInt(el.dataset.target);
    let current = 0;
    const step = Math.ceil(target / 50);
    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      el.textContent = current;
      if (current >= target) clearInterval(timer);
    }, 30);
  });
}

// ---- PRICE TABLE ----
function getChange(price, prev) {
  if (price > prev) return { label: `▲ ₹${(price - prev).toLocaleString("en-IN")}`, cls: "change-up" };
  if (price < prev) return { label: `▼ ₹${(prev - price).toLocaleString("en-IN")}`, cls: "change-down" };
  return { label: "—", cls: "change-flat" };
}

function renderPriceTable() {
  const tbody = document.getElementById("priceTableBody");
  tbody.innerHTML = mandiPrices.map(p => {
    const ch = getChange(p.price, p.prev);
    return `
      <tr>
        <td><strong>${p.name}</strong></td>
        <td><span class="cat-pill">${p.category}</span></td>
        <td>₹ ${p.price.toLocaleString("en-IN")}</td>
        <td>/ ${p.unit}</td>
        <td class="${ch.cls}">${ch.label}</td>
        <td>Today</td>
      </tr>
    `;
  }).join("");
}

// ---- TICKER ----
function renderTicker() {
  const track = document.getElementById("tickerTrack");
  const items = mandiPrices.map(p => {
    const ch = getChange(p.price, p.prev);
    const arrow = p.price > p.prev ? "▲" : p.price < p.prev ? "▼" : "—";
    const cls   = p.price > p.prev ? "t-up" : p.price < p.prev ? "t-down" : "";
    return `<span class="ticker-item">
      <span class="t-name">${p.name}</span>&nbsp;
      <span class="t-price">₹${p.price.toLocaleString("en-IN")}</span>&nbsp;
      <span class="${cls}">${arrow}</span>
    </span>`;
  }).join("");
  // duplicate for seamless loop
  track.innerHTML = `<div class="ticker-inner">${items}${items}</div>`;
}

// ---- CARD PRICES ----
function updateCardPrices() {
  mandiPrices.forEach(p => {
    const el = document.querySelector(`[data-product="${p.product}"]`);
    if (el) el.textContent = `₹ ${p.price.toLocaleString("en-IN")}`;
  });
}

function updateLastUpdated() {
  const now = new Date();
  document.getElementById("lastUpdated").textContent =
    `Prices last updated: ${now.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })} IST — Source: lowest available across Indian mandis`;
}

// ---- PRODUCT SEARCH & FILTER ----
const searchInput  = document.getElementById("productSearch");
const categoryFilter = document.getElementById("categoryFilter");
const grid         = document.getElementById("productsGrid");
const cards        = () => grid.querySelectorAll(".product-card");
const noResults    = document.getElementById("noResults");

function filterProducts() {
  const query = searchInput.value.toLowerCase().trim();
  const cat   = categoryFilter.value;

  let visible = 0;
  cards().forEach(card => {
    const name    = card.dataset.name.toLowerCase();
    const cardCat = card.dataset.cat;
    const matchQ  = !query || name.includes(query);
    const matchC  = cat === "all" || cardCat === cat;
    const show    = matchQ && matchC;
    card.style.display = show ? "" : "none";
    if (show) visible++;
  });
  noResults.style.display = visible === 0 ? "block" : "none";
}

searchInput.addEventListener("input", filterProducts);
categoryFilter.addEventListener("change", (e) => {
  // sync tabs
  document.querySelectorAll(".cat-tab").forEach(t => {
    t.classList.toggle("active", t.dataset.cat === e.target.value);
  });
  filterProducts();
});

// Category tabs
document.querySelectorAll(".cat-tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".cat-tab").forEach(t => t.classList.remove("active"));
    btn.classList.add("active");
    categoryFilter.value = btn.dataset.cat;
    filterProducts();
  });
});

// ---- MODAL ----
function openEnquiry(productName) {
  document.getElementById("modalProductName").textContent = `Product: ${productName}`;
  document.getElementById("fProduct").value = productName; // prefill main form too
  document.getElementById("modalOverlay").classList.add("open");
  document.body.style.overflow = "hidden";
}
function closeModal() {
  document.getElementById("modalOverlay").classList.remove("open");
  document.body.style.overflow = "";
}
function submitModal() {
  const name  = document.getElementById("mName").value.trim();
  const email = document.getElementById("mEmail").value.trim();
  if (!name || !email) { alert("Please enter your name and email."); return; }
  // TODO: POST to backend /api/enquiry
  alert("✅ Enquiry sent! Our team will reach you within 2 hours.");
  closeModal();
}
window.openEnquiry = openEnquiry;
window.closeModal  = closeModal;
window.submitModal = submitModal;

// ---- MAIN ENQUIRY FORM ----
function submitForm(e) {
  e.preventDefault();
  const data = {
    name:    document.getElementById("fName").value,
    company: document.getElementById("fCompany").value,
    email:   document.getElementById("fEmail").value,
    country: document.getElementById("fCountry").value,
    product: document.getElementById("fProduct").value,
    qty:     document.getElementById("fQty").value,
    pack:    document.getElementById("fPack").value,
    message: document.getElementById("fMsg").value,
  };
  console.log("Enquiry data (send to backend):", data);
  // TODO: fetch("/api/enquiry", { method:"POST", body: JSON.stringify(data) })
  alert("✅ Thank you! We'll get back to you within 2 hours.");
  document.getElementById("enquiryForm").reset();
}
window.submitForm = submitForm;

// ---- SCROLL REVEAL ----
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.style.opacity    = "1";
      entry.target.style.transform  = "translateY(0)";
    }
  });
}, { threshold: 0.1 });

document.querySelectorAll(".why-card, .cert-card, .product-card").forEach(el => {
  el.style.opacity   = "0";
  el.style.transform = "translateY(20px)";
  el.style.transition = "opacity .5s ease, transform .5s ease";
  revealObserver.observe(el);
});

// ---- INIT ----
renderPriceTable();
updateCardPrices();
renderTicker();
updateLastUpdated();

// Live fluctuation every 15 seconds
setInterval(simulateLiveFluctuation, 15000);
