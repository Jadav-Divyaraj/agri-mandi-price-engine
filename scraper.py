"""
AgroReach India — Mandi Price Extraction & Statistical Cleansing Engine

Overview:
Aggregates wholesale commodity rates from official Indian market networks
(Agmarknet and Open Government Data Platform - data.gov.in).

Key Pipeline Steps:
1. Multi-Source Ingestion: Primary API query with secondary HTML fallback.
2. Anomaly Elimination: Range validation table (PRICE_RANGE) to resolve unit
   mismatches (e.g., kg vs quintal).
3. Statistical Outlier Rejection: Dynamic median and standard deviation (2.5 sigma)
   filtering to eliminate data entry noise.
4. Temporal Fallback: Sliding 5-day window for market closures and holidays.
"""

import requests
import json
import os
import time
import statistics
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

API_KEY      = os.getenv("DATA_GOV_API_KEY", "579b464db66ec23bdd000001bf3ce4c4217e41dd6d3a8741ba5e176e")
OUTPUT_FILE  = "prices.json"
HISTORY_FILE = "price_history.json"
TIMEOUT      = 30
MAX_DAYS     = 5

# Realistic price ranges per commodity (Rs/quintal).
# Prices outside these are garbage data — filtered out.
PRICE_RANGE = {
    "cumin":         (15000, 60000),
    "turmeric":      (5000,  30000),
    "chilli":        (3000,  40000),
    "coriander":     (4000,  20000),
    "pepper":        (30000, 100000),
    "cardamom":      (80000, 300000),
    "ginger":        (3000,  25000),
    "garlic":        (2000,  50000),
    "mustard":       (4000,  10000),
    "fenugreek":     (3000,  12000),
    "fennel":        (5000,  20000),
    "ajwain":        (8000,  30000),
    "mango":         (500,   80000),
    "pomegranate":   (3000,  40000),
    "grapes":        (1000,  20000),
    "banana":        (500,   8000),
    "apple":         (2000,  20000),
    "coconut":       (1000,  8000),
    "watermelon":    (200,   3000),
    "orange":        (500,   10000),
    "papaya":        (300,   5000),
    "guava":         (400,   5000),
    "onion":         (200,   8000),
    "potato":        (200,   5000),
    "tomato":        (100,   8000),
    "greenchilli":   (500,   15000),
    "cauliflower":   (200,   4000),
    "capsicum":      (500,   8000),
    "carrot":        (300,   5000),
    "brinjal":       (100,   4000),
    "ladyfinger":    (500,   8000),
    "peas":          (500,   10000),
    "basmati":       (2000,  12000),
    "wheat":         (1800,  4000),
    "maize":         (1200,  4000),
    "chana":         (3000,  10000),
    "soybean":       (3000,  8000),
    "tur":           (5000,  15000),
    "moong":         (5000,  15000),
    "urad":          (5000,  15000),
    "masoor":        (4000,  12000),
    "bajra":         (1500,  4000),
    "rajma":         (6000,  20000),
    "jowar":         (1500,  5000),
    "cashew":        (50000, 200000),
    "almonds":       (40000, 120000),
    "walnut":        (50000, 150000),
    "raisins":       (8000,  30000),
    "dates":         (5000,  25000),
    "groundnut":     (4000,  10000),
    "sesame":        (8000,  25000),
    "castorseed":    (4000,  10000),
    "sunflowerseed": (3000,  8000),
    "copra":         (8000,  25000),
    "cottonseed":    (2000,  7000),
    "coffee":        (15000, 80000),
    "rubber":        (12000, 25000),
    "marigold":      (200,   4000),
    "sugarcane":     (200,   600),
    "honey":         (5000,  25000),
}

COMMODITIES = {
    "spices": [
        {"key":"cumin",     "name":"Cumin Seeds",       "agmark":"Jeera"},
        {"key":"turmeric",  "name":"Turmeric",          "agmark":"Turmeric"},
        {"key":"chilli",    "name":"Red Chilli",        "agmark":"Dry Chillies"},
        {"key":"coriander", "name":"Coriander Seeds",   "agmark":"Coriander"},
        {"key":"pepper",    "name":"Black Pepper",      "agmark":"Black pepper"},
        {"key":"cardamom",  "name":"Cardamom",          "agmark":"Cardamom"},
        {"key":"ginger",    "name":"Ginger (Dry)",      "agmark":"Ginger(Dry)"},
        {"key":"garlic",    "name":"Garlic",            "agmark":"Garlic"},
        {"key":"mustard",   "name":"Mustard Seeds",     "agmark":"Mustard"},
        {"key":"fenugreek", "name":"Fenugreek",         "agmark":"Methi"},
        {"key":"fennel",    "name":"Fennel Seeds",      "agmark":"Saunf"},
        {"key":"ajwain",    "name":"Ajwain",            "agmark":"Ajwan"},
    ],
    "fruits": [
        {"key":"mango",       "name":"Mango",           "agmark":"Mango"},
        {"key":"pomegranate", "name":"Pomegranate",     "agmark":"Pomegranate"},
        {"key":"grapes",      "name":"Grapes",          "agmark":"Grapes"},
        {"key":"banana",      "name":"Banana",          "agmark":"Banana"},
        {"key":"apple",       "name":"Apple",           "agmark":"Apple"},
        {"key":"coconut",     "name":"Coconut",         "agmark":"Coconut"},
        {"key":"watermelon",  "name":"Watermelon",      "agmark":"Water Melon"},
        {"key":"orange",      "name":"Orange",          "agmark":"Orange"},
        {"key":"papaya",      "name":"Papaya",          "agmark":"Papaya"},
        {"key":"guava",       "name":"Guava",           "agmark":"Guava"},
    ],
    "vegetables": [
        {"key":"onion",       "name":"Onion",           "agmark":"Onion"},
        {"key":"potato",      "name":"Potato",          "agmark":"Potato"},
        {"key":"tomato",      "name":"Tomato",          "agmark":"Tomato"},
        {"key":"greenchilli", "name":"Green Chilli",    "agmark":"Green Chilli"},
        {"key":"cauliflower", "name":"Cauliflower",     "agmark":"Cauliflower"},
        {"key":"capsicum",    "name":"Capsicum",        "agmark":"Capsicum"},
        {"key":"carrot",      "name":"Carrot",          "agmark":"Carrot"},
        {"key":"brinjal",     "name":"Brinjal",         "agmark":"Brinjal"},
        {"key":"ladyfinger",  "name":"Lady Finger",     "agmark":"Bhindi(Ladies Finger)"},
        {"key":"peas",        "name":"Green Peas",      "agmark":"Green Peas"},
    ],
    "grains": [
        {"key":"basmati",  "name":"Basmati Rice",       "agmark":"Rice"},
        {"key":"wheat",    "name":"Wheat",              "agmark":"Wheat"},
        {"key":"maize",    "name":"Maize",              "agmark":"Maize"},
        {"key":"chana",    "name":"Chana (Gram)",       "agmark":"Gram"},
        {"key":"soybean",  "name":"Soybean",            "agmark":"Soyabean"},
        {"key":"tur",      "name":"Tur Dal",            "agmark":"Tur"},
        {"key":"moong",    "name":"Moong Dal",          "agmark":"Moong (Whole)"},
        {"key":"urad",     "name":"Urad Dal",           "agmark":"Black Gram (Urd Beans)(Whole)"},
        {"key":"masoor",   "name":"Masoor Dal",         "agmark":"Masur Dal"},
        {"key":"bajra",    "name":"Bajra",              "agmark":"Bajra(Pearl Millet/Cumbu)"},
        {"key":"rajma",    "name":"Rajma",              "agmark":"Rajma (Kidney Beans)"},
        {"key":"jowar",    "name":"Jowar",              "agmark":"Jowar(Sorghum)"},
    ],
    "dryfruits": [
        {"key":"cashew",  "name":"Cashew W320",         "agmark":"Cashewnuts"},
        {"key":"almonds", "name":"Almonds",             "agmark":"Almond"},
        {"key":"walnut",  "name":"Walnut",              "agmark":"Walnut"},
        {"key":"raisins", "name":"Raisins",             "agmark":"Dry Grapes"},
        {"key":"dates",   "name":"Dates",               "agmark":"Dates"},
    ],
    "oils": [
        {"key":"groundnut",     "name":"Groundnut",     "agmark":"Groundnut"},
        {"key":"sesame",        "name":"Sesame Seeds",  "agmark":"Sesamum(Sesame,Gingelly,Til)"},
        {"key":"castorseed",    "name":"Castor Seed",   "agmark":"Castor Seed"},
        {"key":"sunflowerseed", "name":"Sunflower Seed","agmark":"Sunflower"},
        {"key":"copra",         "name":"Copra",         "agmark":"Copra"},
        {"key":"cottonseed",    "name":"Cotton Seed",   "agmark":"Cotton"},
    ],
    "others": [
        {"key":"coffee",    "name":"Coffee",            "agmark":"Coffee"},
        {"key":"rubber",    "name":"Rubber",            "agmark":"Rubber"},
        {"key":"marigold",  "name":"Marigold",          "agmark":"Marigold(Loose)"},
        {"key":"sugarcane", "name":"Sugarcane",         "agmark":"Sugarcane"},
        {"key":"honey",     "name":"Honey",             "agmark":"Honey"},
    ],
}


def is_valid(key, price):
    lo, hi = PRICE_RANGE.get(key, (50, 999999))
    return lo <= price <= hi


def clean_and_aggregate(key, triples):
    """Filter bad records, remove outliers, return best price."""
    valid = [(mn, mx, mo) for mn, mx, mo in triples
             if is_valid(key, mo) and mn > 0 and mx > 0]
    if not valid:
        return None
    if len(valid) >= 5:
        modals = [mo for _, _, mo in valid]
        med    = statistics.median(modals)
        sd     = statistics.stdev(modals) if len(modals) > 1 else med * 0.3
        valid  = [(mn, mx, mo) for mn, mx, mo in valid
                  if abs(mo - med) <= 2.5 * max(sd, med * 0.2)]
    if not valid:
        return None
    return {
        "min":     int(min(mn for mn, _, _ in valid)),
        "max":     int(max(mx for _, mx, _ in valid)),
        "modal":   int(min(mo for _, _, mo in valid)),
        "markets": len(valid),
    }


# ── Source 1: data.gov.in API ─────────────────────────────
API_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"

def fetch_api(key, agmark):
    for days in range(MAX_DAYS):
        date = (datetime.now() - timedelta(days=days)).strftime("%d/%m/%Y")
        try:
            r = requests.get(API_URL, params={
                "api-key": API_KEY, "format": "json", "limit": 500,
                "filters[Commodity]": agmark,
                "filters[Arrival_Date]": date,
            }, timeout=TIMEOUT)
            r.raise_for_status()
            recs = r.json().get("records", [])
            triples = []
            for rec in recs:
                try:
                    mn = float(rec.get("Min_Price")   or 0)
                    mx = float(rec.get("Max_Price")   or 0)
                    mo = float(rec.get("Modal_Price") or 0)
                    if mo > 0:
                        triples.append((mn, mx, mo))
                except (ValueError, TypeError):
                    pass
            res = clean_and_aggregate(key, triples)
            if res:
                res["date"] = date
                res["source"] = "data.gov.in"
                return res
        except requests.Timeout:
            print("(timeout)", end=" ", flush=True)
        except Exception:
            pass
        time.sleep(0.3)
    return None


# ── Source 2: agmarknet.gov.in HTML scrape ────────────────
AGMK_URL = "https://agmarknet.gov.in/SearchCmmMkt.aspx"
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
       "Accept-Language": "en-IN,en;q=0.9"}

def fetch_agmarknet(key, agmark):
    for days in range(3):
        ds = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
        try:
            r = requests.get(AGMK_URL, headers=HDR, timeout=TIMEOUT, params={
                "Tx_Commodity":"0","Tx_State":"0","Tx_District":"0","Tx_Market":"0",
                "DateFrom":ds,"DateTo":ds,"Fr_Date":ds,"To_Date":ds,"Tx_Trend":"0",
                "Tx_CommodityHead":agmark,"Tx_StateHead":"--Select--",
                "Tx_DistrictHead":"--Select--","Tx_MarketHead":"--Select--",
            })
            soup  = BeautifulSoup(r.text, "html.parser")
            table = soup.find("table", {"id":"cphBody_GridPriceData"})
            if not table:
                time.sleep(1)
                continue
            triples = []
            for row in table.find_all("tr")[1:]:
                cols = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cols) >= 9:
                    try:
                        mn = float(cols[6].replace(",",""))
                        mx = float(cols[7].replace(",",""))
                        mo = float(cols[8].replace(",",""))
                        if mo > 0:
                            triples.append((mn, mx, mo))
                    except ValueError:
                        pass
            res = clean_and_aggregate(key, triples)
            if res:
                res["date"] = ds
                res["source"] = "agmarknet.gov.in"
                return res
        except Exception:
            pass
        time.sleep(1.5)
    return None


# ── History ───────────────────────────────────────────────
def load_history():
    return json.load(open(HISTORY_FILE)) if os.path.exists(HISTORY_FILE) else {}

def save_history(h):
    json.dump(h, open(HISTORY_FILE,"w"), indent=2)

def push_history(h, key, modal, date):
    h.setdefault(key, [])
    if not h[key] or h[key][-1]["date"] != date:
        h[key].append({"price": modal, "date": date})
    h[key] = h[key][-7:]
    return h


# ── Main ──────────────────────────────────────────────────
def main():
    print("="*65)
    print("  AgroReach Mandi Scraper & Cleansing Engine")
    print(f"  {datetime.now().strftime('%d %b %Y  %H:%M IST')}")
    print("="*65)

    history = load_history()
    output = {
        "generated_at": datetime.now().isoformat(),
        "source": "Agmarknet (data.gov.in + direct scrape)",
        "note": "Lowest validated modal price. Mandi name undisclosed.",
        "categories": {},
    }

    total = sum(len(v) for v in COMMODITIES.values())
    done = ok = failed = 0

    for cat, items in COMMODITIES.items():
        print(f"\n── {cat.upper()} ──")
        output["categories"][cat] = []
        for p in items:
            done += 1
            print(f"  [{done:2}/{total}] {p['name']}...", end=" ", flush=True)

            res = fetch_api(p["key"], p["agmark"])
            if not res:
                print("→ scraping...", end=" ", flush=True)
                res = fetch_agmarknet(p["key"], p["agmark"])

            if res:
                ok += 1
                history = push_history(history, p["key"], res["modal"], res["date"])
                entry = {
                    "key": p["key"], "name": p["name"], "category": cat,
                    "min": res["min"], "max": res["max"], "modal": res["modal"],
                    "unit": "quintal", "date": res["date"],
                    "source": res["source"], "markets": res.get("markets", 1),
                    "history": history.get(p["key"], []), "stale": False,
                }
                print(f"✅  Min:₹{res['min']:,}  Max:₹{res['max']:,}  "
                      f"Low:₹{res['modal']:,}  [{res['date']} · {res['markets']} mandis]")
            else:
                failed += 1
                last = history.get(p["key"], [{}])[-1].get("price", 0) if history.get(p["key"]) else 0
                entry = {
                    "key": p["key"], "name": p["name"], "category": cat,
                    "min": 0, "max": 0, "modal": last,
                    "unit": "quintal", "date": "N/A",
                    "source": "none", "markets": 0,
                    "history": history.get(p["key"], []), "stale": True,
                }
                print(f"❌  No data  (last known: ₹{last:,})")

            output["categories"][cat].append(entry)
            time.sleep(0.5)

    json.dump(output, open(OUTPUT_FILE,"w",encoding="utf-8"), indent=2, ensure_ascii=False)
    save_history(history)

    print("\n" + "="*65)
    print(f"  ✅  Fetched  : {ok}/{total}")
    print(f"  ❌  No data  : {failed}  (fallback prices preserved)")
    print(f"  💾  Saved    : {OUTPUT_FILE}")
    print("="*65)


if __name__ == "__main__":
    main()
