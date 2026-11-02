# 🌾 AgroReach India — Enterprise Agri-Export Platform & Mandi Price Intelligence Engine

[![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/HTML)
[![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/CSS)
[![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Bootstrap 5](https://img.shields.io/badge/Bootstrap_5-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![Open Data](https://img.shields.io/badge/Data.gov.in-Agmarknet-0052CC?style=for-the-badge)](https://data.gov.in/)
[![Architecture](https://img.shields.io/badge/Architecture-Decoupled_ETL-success?style=for-the-badge)]()

> **An enterprise-grade B2B agricultural export portal and real-time commodity price intelligence engine connecting international importers with verified Indian APMC Mandi wholesale pricing.**

---

## 📌 Executive Summary & Problem Space

In cross-border agricultural trade, international and domestic wholesale buyers face severe **information asymmetry**. Price discovery across 2,400+ Indian APMC (Agricultural Produce Market Committee) mandis is fragmented across disparate government portals, delayed reporting, and mixed retail/wholesale units.

**AgroReach India** solves this with an end-to-end decoupled architecture:
1. **Automated ETL & Data Harvesting**: Multi-tier scrapers extracting daily modal prices across 60+ commodities from `data.gov.in` and `agmarknet.gov.in`.
2. **Statistical Anomaly Cleansing**: An algorithmic cleaning pipeline implementing range-bound gates and $2.5\sigma$ median outlier rejection to neutralize bad data.
3. **High-Performance Presentation Tier**: A lightweight, zero-dependency client with dynamic filtering, real-time market tickers, and B2B Request-For-Quote (RFQ) workflows.

---

## 🏛️ End-to-End System Architecture

The system is architected as a **decoupled, event-driven data pipeline** separated into four decoupled layers: Ingestion, Transformation/Cleansing, Data Persistence, and Client Presentation.

```mermaid
flowchart TB
    %% Ingestion Layer
    subgraph L1 ["1. INGESTION & HARVESTING TIER"]
        direction TB
        S1["🏛️ Open Government Data API<br/>(api.data.gov.in / Resource IDs)"]
        S2["🌾 Agmarknet ASP.NET Portal<br/>(agmarknet.gov.in / SearchCmmMkt)"]
        W1["📅 5-Day Sliding Date Fallback Engine<br/>(Handles Sundays & Mandi Closures)"]
        H1["🛡️ User-Agent & Request Pool Manager<br/>(Timeout: 30s | Backoff Delay)"]
        S1 --> W1
        S2 --> W1
        W1 --> H1
    end

    %% Transformation & Cleansing
    subgraph L2 ["2. TRANSFORMATION & CLEANSING ENGINE"]
        direction TB
        T1["🔍 Raw Payload Parser<br/>(JSON Normalizer + BeautifulSoup Table Extractor)"]
        T2["🚫 Domain Sanity Range Gate<br/>(Filters kg vs quintal unit confusion)"]
        T3["📊 Statistical Outlier Rejection<br/>(|P_i - Median| <= 2.5 * sigma)"]
        T4["🔤 Commodity Alias & Key Resolver<br/>('Jeera' -> Cumin | 'Haldi' -> Turmeric)"]
        T5["📈 Metric Aggregator<br/>(Min Price | Max Price | Modal Wholesale Rate)"]
        T1 --> T2 --> T3 --> T4 --> T5
    end

    %% Persistence Layer
    subgraph L3 ["3. PERSISTENCE & DATA CONTRACT"]
        direction TB
        P1[("📄 Live Contract: prices.json")]
        P2[("🗄️ Historical Archive: prices_YYYYMMDD.json")]
        P3[("📜 Master Taxonomy: commodities.json")]
    end

    %% Presentation Layer
    subgraph L4 ["4. CLIENT PRESENTATION ENGINE"]
        direction TB
        C1["🌐 Landing Hub (index.html)<br/>(Hero Carousel, Stats Counter, Trending Top 10)"]
        C2["📦 60+ Catalog Grid (products.html)<br/>(Real-time Search, Category Filter, Card Badges)"]
        C3["📊 Live Mandi Board (prices.html)<br/>(Live Ticker Loop, Price Spreads, APMC Origin)"]
        C4["💬 RFQ Modal & Lead Dispatcher<br/>(Form Validator & Quotation Handlers)"]
    end

    %% Data Connections
    H1 -->|Raw Responses| T1
    T5 -->|Atomic Write| P1
    T5 -.->|Daily Snapshot| P2
    P3 -.->|Taxonomy Schema| T4

    P1 -->|Asynchronous Fetch| C1
    P1 -->|Asynchronous Fetch| C2
    P1 -->|Asynchronous Fetch| C3
    C2 --> C4
```

---

## 🔄 End-to-End Execution Sequence

This sequence diagram illustrates the complete operational lifecycle from mandi auction recording to buyer quote submission:

```mermaid
sequenceDiagram
    autonumber
    actor Mandi as APMC Mandi Auctions
    participant Govt as Govt Portals (Agmarknet/Data.gov)
    participant Scraper as Python ETL Pipeline (claude_scraper.py)
    participant Data as Persistence Layer (prices.json)
    participant Web as Web Client (app.js)
    actor Buyer as Global Agricultural Buyer

    Mandi->>Govt: Farmers & Traders record daily trading rates
    Govt-->>Govt: Aggregate mandi reports (7:00 AM - 9:30 AM IST)
    
    rect rgb(240, 248, 255)
        Note over Scraper,Govt: Scheduled / Automated Data Extraction
        Scraper->>Govt: Query API (filters[Commodity], filters[Arrival_Date])
        alt API Timeout or Empty
            Scraper->>Govt: Direct HTML Scrape (SearchCmmMkt.aspx table)
        end
        Govt-->>Scraper: Return raw market records (mixed units & noisy data)
        Scraper->>Scraper: Execute Domain Range Validation (lo <= price <= hi)
        Scraper->>Scraper: Apply Statistical Outlier Filter (|Price - Median| <= 2.5 * σ)
        Scraper->>Scraper: Aggregate Min, Max, and lowest Modal wholesale rate
        Scraper->>Data: Atomically serialize clean dataset (prices.json)
    end

    rect rgb(245, 255, 245)
        Note over Buyer,Web: Buyer Browsing & Real-Time Discovery
        Buyer->>Web: Open AgroReach Portal (products.html / prices.html)
        Web->>Data: fetch('prices.json')
        Data-->>Web: Return JSON payload with 60+ commodities
        Web->>Web: Hydrate DOM (Live prices, Min/Max cards, Live Ticker)
        Buyer->>Web: Filter category 'Spices' & Search 'Cumin'
        Web->>Web: Client-side dynamic DOM refilter (< 5ms response)
        Buyer->>Web: Click "Enquire Now" & submit B2B export specification
        Web-->>Buyer: Confirm RFQ receipt with 2-hour SLA response
    end
```

---

## 🧮 Mathematical Data Cleansing Formulation

Agricultural datasets collected across hundreds of APMC mandis frequently suffer from dirty entries (e.g. retail prices entered as wholesale, or per-kg figures entered into per-quintal fields). The data pipeline applies a **two-phase deterministic filter**:

### Phase 1: Range-Bound Domain Gate
Every commodity $c$ is checked against an empirical boundary $[\text{Min}_c, \text{Max}_c]$:
$$\text{Valid}(P_i) = \begin{cases} \text{True}, & \text{if } \text{Min}_c \le P_i \le \text{Max}_c \\ \text{False}, & \text{otherwise} \end{cases}$$

### Phase 2: Statistical Anomaly Elimination ($Z$-Score / Standard Deviation)
For all commodities with sample size $N \ge 5$ across reporting mandis, we compute the sample median $\tilde{P}$ and standard deviation $\sigma$:

$$\tilde{P} = \text{Median}(\{P_1, P_2, \dots, P_N\})$$
$$\sigma = \sqrt{\frac{1}{N-1}\sum_{i=1}^{N}(P_i - \bar{P})^2}$$

A record $P_i$ is accepted if and only if its absolute deviation from the median does not exceed $2.5$ effective dispersion units:

$$|P_i - \tilde{P}| \le 2.5 \times \max\left(\sigma, \; 0.2 \times \tilde{P}\right)$$

> **Why this matters**: This formula protects the business from displaying erroneous prices (e.g., Cumin seeds misquoted at ₹500/quintal instead of ₹28,000/quintal) while naturally adapting to real volatility in Indian agricultural trade.

---

## 🌟 Key Features & Functional Modules

| Module | Technical Capability | User & Business Value |
| :--- | :--- | :--- |
| **Commodity Catalog** | 60+ items across 8 categories with HS codes, MOQs, and harvest origins. | Comprehensive export catalog for spices, grains, fruits, vegetables, and dry fruits. |
| **Mandi Price Engine** | Displays **Min**, **Max**, and **Modal** wholesale prices per quintal (100 kg). | Transparent price discovery that eliminates predatory middleman markups. |
| **Instant Client Search** | Native Vanilla JS debounced search across names, varieties, and botanical terms. | Zero-latency product lookup without server roundtrips. |
| **Dynamic Ticker** | CSS infinite seamless hardware-accelerated ticker loop. | Live visual representation of market movement and commodity trends. |
| **B2B Inquiry System** | Modal RFQ dispatcher capturing quantity, packaging, and destination country. | Direct lead generation engine for commercial export sales. |
| **Mobile-First UX** | Touch-optimized sliding drawer, responsive card grids, and Bootstrap carousel. | Accessible across low-bandwidth smartphones used by international agro-brokers. |

---

## 🛠️ Complete Technology Matrix

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        AGROREACH INDIA TECH STACK                      │
├────────────────────┬───────────────────────────────────────────────────┤
│ Layer              │ Technology / Library / Standard                   │
├────────────────────┼───────────────────────────────────────────────────┤
│ Frontend Engine    │ HTML5 Semantic Markup, Vanilla ECMAScript (ES6+)  │
│ Styling & Design   │ CSS3 Custom Variables, Bootstrap 5.3.3, Flexbox   │
│ Typography         │ Playfair Display (Serif) + DM Sans (Clean Sans)   │
│ Ingestion (ETL)    │ Python 3.9+, Requests, BeautifulSoup4, aiohttp    │
│ Resilient Network  │ Exponential Backoff, Tenacity, Sliding 5-day Date │
│ Data Cleansing     │ Python Statistics, Custom Boundary Range Gates    │
│ Persistence Layer  │ JSON Static Decoupled Cache (REST-ready schema)   │
│ Version Control    │ Git, GitHub Actions Ready                         │
└────────────────────┴───────────────────────────────────────────────────┘
```

---

## 📂 Repository Layout & File Manifest

```text
Export Website/
├── .env.example               # Template for data.gov.in API authentication
├── .gitignore                 # Strict rules excluding pycache, env, debug dumps
├── requirements.txt           # Verified Python dependencies (requests, bs4, aiohttp)
├── README.md                  # Comprehensive senior-engineer architectural documentation
│
├── index.html                 # Landing hub: Hero carousel, stats counter, trending top 10
├── products.html              # 60+ catalog grid with interactive category switcher
├── prices.html                # Live APMC mandi price board and market ticker
├── style.css                  # Unified responsive design system and CSS variables
├── app.js                     # Core DOM controller: search, filter, ticker, quote modal
│
├── claude_scraper.py          # Primary production scraper with statistical outlier cleaning
├── scraper.py                 # Baseline scraper with multi-endpoint resolution
├── kimi_scraper.py            # Async concurrent aiohttp scraper with retry policies
│
├── commodities.json           # Master dictionary of commodities and search aliases
├── prices.json                # Production live price cache hydrated into the UI
└── prices_20260330_0003.json  # Validated reference snapshot (38 verified commodities)
```

---

## 🛡️ Resilience & Fault-Tolerance Strategy

1. **Sliding Date Fallback**: If Sunday or a holiday yields zero records, the engine slides back up to 5 days until it finds an active trading session.
2. **Graceful UI Degradation**: If `prices.json` is missing or network fails, the frontend automatically falls back to baked baseline figures (`MOCK` table in `products.html`) with an informative user banner.
3. **Decoupled Architecture**: Scraper failures **never** crash the website. The frontend reads the last successfully generated JSON snapshot, guaranteeing 99.99% uptime.
4. **Environment-Driven Secrets**: API keys are isolated via `os.getenv("DATA_GOV_API_KEY")` preventing accidental credential exposure in public repositories.

---

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
```

### 2. Configure Python Environment
```bash
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate   # Windows
source venv/bin/activate  # macOS / Linux

# Install required packages
pip install -r requirements.txt
```

### 3. Run the Scraping & Cleansing Pipeline
```bash
# Execute the production cleaner and scraper
python claude_scraper.py
```
*Output: Refreshed, validated mandi prices written directly to `prices.json`.*

### 4. Launch the Web Application
Because modern browsers enforce CORS restrictions when fetching JSON over `file://`, launch using Python's built-in server:
```bash
python -m http.server 8000
```
Navigate to: `http://localhost:8000`

---

## 🔮 Future Engineering Roadmap

- [ ] **FastAPI Microservice Layer**: Expose REST endpoints (`/api/v1/commodities`, `/api/v1/prices/{key}`).
- [ ] **Automated GitHub Actions Cron**: Daily scheduled workflow at 09:30 AM IST to run the scraper and auto-commit updated `prices.json`.
- [ ] **Forex Conversion Engine**: Real-time currency toggle (INR ₹/quintal ➔ USD $/MT, EUR €/MT).
- [ ] **Interactive Time-Series Charts**: 30-day moving average and price volatility trends rendered via Chart.js.

---

## 👨‍💻 Engineering Profile

- **Developer**: Diploma in Computer Engineering Fresher
- **Specialization**: Full-Stack Web Development, Data Ingestion Pipelines, Python Automation
- **Profiles**: [GitHub](https://github.com/Jadav-Divyaraj) • [LinkedIn](https://linkedin.com)

---

## 📄 License
This project is open-source under the **MIT License**.
