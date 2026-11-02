"""
AgroReach India — Asynchronous High-Concurrency Mandi Price Scraper
Leverages aiohttp connection pooling, asyncio semaphores, and exponential backoff.
"""

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

import aiohttp
import aiofiles
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# COMPLETE COMMODITY CONFIGURATION (All 50+ items)
COMMODITIES_CONFIG = {
    "spices": [
        {"key": "cumin", "name": "Cumin Seeds", "api_names": ["Jeera", "Cumin"]},
        {"key": "turmeric", "name": "Turmeric", "api_names": ["Turmeric", "Haldi"]},
        {"key": "chilli", "name": "Red Chilli", "api_names": ["Dry Chillies", "Red Chilli", "Mirchi"]},
        {"key": "coriander", "name": "Coriander Seeds", "api_names": ["Coriander", "Dhaniya"]},
        {"key": "pepper", "name": "Black Pepper", "api_names": ["Black Pepper", "Kali Mirch"]},
        {"key": "cardamom", "name": "Cardamom", "api_names": ["Cardamom", "Elaichi"]},
        {"key": "ginger", "name": "Ginger (Dry)", "api_names": ["Ginger"]},
        {"key": "garlic", "name": "Garlic", "api_names": ["Garlic", "Lahsun"]},
        {"key": "mustard", "name": "Mustard Seeds", "api_names": ["Mustard", "Sarson"]},
        {"key": "fenugreek", "name": "Fenugreek", "api_names": ["Fenugreek", "Methi"]},
        {"key": "fennel", "name": "Fennel Seeds", "api_names": ["Fennel", "Saunf"]},
        {"key": "ajwain", "name": "Ajwain", "api_names": ["Ajwain", "Carom"]},
    ],
    "fruits": [
        {"key": "mango", "name": "Alphonso Mango", "api_names": ["Mango"]},
        {"key": "pomegranate", "name": "Pomegranate", "api_names": ["Pomegranate", "Anar"]},
        {"key": "grapes", "name": "Grapes", "api_names": ["Grapes"]},
        {"key": "banana", "name": "Banana", "api_names": ["Banana"]},
        {"key": "apple", "name": "Apple", "api_names": ["Apple"]},
        {"key": "coconut", "name": "Coconut", "api_names": ["Coconut", "Nariyal"]},
        {"key": "orange", "name": "Orange", "api_names": ["Orange", "Santara"]},
        {"key": "papaya", "name": "Papaya", "api_names": ["Papaya"]},
        {"key": "guava", "name": "Guava", "api_names": ["Guava", "Amrud"]},
        {"key": "watermelon", "name": "Watermelon", "api_names": ["Watermelon", "Tarbuj"]},
    ],
    "vegetables": [
        {"key": "onion", "name": "Onion", "api_names": ["Onion", "Pyaz"]},
        {"key": "potato", "name": "Potato", "api_names": ["Potato", "Aloo"]},
        {"key": "tomato", "name": "Tomato", "api_names": ["Tomato", "Tamatar"]},
        {"key": "greenchilli", "name": "Green Chilli", "api_names": ["Green Chilli", "Hari Mirch"]},
        {"key": "cauliflower", "name": "Cauliflower", "api_names": ["Cauliflower", "Phool Gobhi"]},
        {"key": "carrot", "name": "Carrot", "api_names": ["Carrot", "Gajar"]},
        {"key": "capsicum", "name": "Capsicum", "api_names": ["Capsicum", "Shimla Mirch"]},
        {"key": "brinjal", "name": "Brinjal", "api_names": ["Brinjal", "Baingan", "Egg Plant"]},
        {"key": "ladyfinger", "name": "Lady Finger", "api_names": ["Bhindi", "Lady Finger", "Okra"]},
    ],
    "grains": [
        {"key": "basmati", "name": "Basmati Rice", "api_names": ["Basmati", "Rice", "Chawal"]},
        {"key": "wheat", "name": "Wheat", "api_names": ["Wheat", "Gehu"]},
        {"key": "maize", "name": "Maize", "api_names": ["Maize", "Makka"]},
        {"key": "chana", "name": "Chana (Gram)", "api_names": ["Gram", "Chana"]},
        {"key": "soybean", "name": "Soybean", "api_names": ["Soybean"]},
        {"key": "tur", "name": "Tur Dal", "api_names": ["Tur", "Arhar", "Pigeon Pea"]},
        {"key": "moong", "name": "Moong Dal", "api_names": ["Moong", "Green Gram"]},
        {"key": "urad", "name": "Urad Dal", "api_names": ["Urad", "Black Gram"]},
        {"key": "bajra", "name": "Bajra", "api_names": ["Bajra", "Pearl Millet"]},
        {"key": "jowar", "name": "Jowar", "api_names": ["Jowar", "Sorghum"]},
    ],
    "dryfruits": [
        {"key": "cashew", "name": "Cashew W320", "api_names": ["Cashew", "Kaju"]},
        {"key": "almonds", "name": "Almonds", "api_names": ["Almond", "Badam"]},
        {"key": "raisins", "name": "Raisins", "api_names": ["Raisins", "Dry Grapes", "Kishmish"]},
        {"key": "walnut", "name": "Walnut", "api_names": ["Walnut", "Akhrot"]},
        {"key": "dates", "name": "Dates", "api_names": ["Dates", "Khajoor"]},
    ],
    "oils": [
        {"key": "groundnut", "name": "Groundnut", "api_names": ["Groundnut", "Moongfali", "Peanut"]},
        {"key": "sesame", "name": "Sesame Seeds", "api_names": ["Sesame", "Til"]},
        {"key": "castorseed", "name": "Castor Seed", "api_names": ["Castor", "Arandi"]},
        {"key": "sunflowerseed", "name": "Sunflower Seed", "api_names": ["Sunflower", "Surajmukhi"]},
    ],
}


@dataclass
class Commodity:
    key: str
    name: str
    api_names: List[str]
    category: str


class MandiPriceScraper:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("DATA_GOV_API_KEY", "579b464db66ec23bdd000001bf3ce4c4217e41dd6d3a8741ba5e176e")
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(5)  # 5 concurrent requests
        
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=20)
        timeout = aiohttp.ClientTimeout(total=20)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/html",
            "Referer": "https://agmarknet.gov.in/",
        }
        self.session = aiohttp.ClientSession(
            connector=connector, 
            timeout=timeout, 
            headers=headers
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def fetch_with_retry(self, url: str, params: Dict = None) -> Optional[Dict]:
        """Fetch with retry logic"""
        for attempt in range(3):
            try:
                async with self.semaphore:
                    async with self.session.get(url, params=params, ssl=False) as resp:
                        if resp.status == 200:
                            content = await resp.text()
                            try:
                                return json.loads(content)
                            except json.JSONDecodeError:
                                # Return raw content for HTML parsing
                                return {"_raw_html": content}
                        elif resp.status == 429:  # Rate limited
                            wait_time = 2 ** attempt
                            logger.warning(f"Rate limited, waiting {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            logger.debug(f"HTTP {resp.status} for {url}")
            except Exception as e:
                logger.debug(f"Attempt {attempt+1} failed: {e}")
                await asyncio.sleep(1)
        return None

    async def get_agmarknet_price(self, commodity: Commodity) -> Optional[Dict]:
        today = datetime.now().strftime("%d-%b-%Y")
        
        endpoints_to_try = [
            "https://agmarknet.gov.in/api/PriceData",
            "https://agmarknet.gov.in/PriceAndArrivals/DatewiseCommodityReport.aspx",
        ]
        
        for endpoint in endpoints_to_try:
            for api_name in commodity.api_names:
                params = {
                    "commodity": api_name,
                    "date": today,
                    "format": "json"
                }
                
                data = await self.fetch_with_retry(endpoint, params)
                if data and not data.get("_raw_html"):
                    result = self._parse_price_data(data, commodity)
                    if result:
                        return result
                
                if data and data.get("_raw_html"):
                    result = self._parse_html_for_prices(data["_raw_html"], commodity)
                    if result:
                        return result
                
                await asyncio.sleep(0.3)
        
        return None

    async def get_datagov_price(self, commodity: Commodity) -> Optional[Dict]:
        resource_ids = [
            "9ef84268-d588-465a-a308-a864a43d0070",
            "de3dbf1d-2a6d-46f0-a4f1-0f4b301b3de4"
        ]
        
        for resource_id in resource_ids:
            url = f"https://api.data.gov.in/resource/{resource_id}"
            params = {
                "api-key": self.api_key,
                "format": "json",
                "limit": "100",
                "filters[commodity]": commodity.name
            }
            
            data = await self.fetch_with_retry(url, params)
            if data and "records" in data:
                records = data["records"]
                if records:
                    return self._process_records(records, commodity)
            
            await asyncio.sleep(0.3)
        
        return None

    def _process_records(self, records: List[Dict], commodity: Commodity) -> Optional[Dict]:
        prices = []
        
        for record in records:
            try:
                modal = record.get('modal_price') or record.get('modal') or record.get('price')
                min_p = record.get('min_price') or record.get('min')
                max_p = record.get('max_price') or record.get('max')
                
                if not modal:
                    continue
                
                modal_val = float(str(modal).replace(',', ''))
                min_val = float(str(min_p).replace(',', '')) if min_p else modal_val
                max_val = float(str(max_p).replace(',', '')) if max_p else modal_val
                
                if 50 < modal_val < 500000:
                    prices.append({
                        "modal": modal_val,
                        "min": min_val,
                        "max": max_val,
                        "market": record.get('market', 'Unknown'),
                        "district": record.get('district', ''),
                        "state": record.get('state', '')
                    })
            except (ValueError, TypeError):
                continue
        
        return self._calculate_stats(prices) if prices else None

    def _parse_price_data(self, data: Any, commodity: Commodity) -> Optional[Dict]:
        if isinstance(data, dict):
            prices_data = data.get('prices') or data.get('data') or data.get('records') or data.get('results')
            if prices_data and isinstance(prices_data, list):
                return self._process_records(prices_data, commodity)
        return None

    def _parse_html_for_prices(self, html: str, commodity: Commodity) -> Optional[Dict]:
        import re
        prices = []
        row_pattern = r'<tr[^>]*>.*?<td[^>]*>([^<]+)</td>.*?<td[^>]*>([^<]+)</td>.*?<td[^>]*>([\d,]+)</td>.*?<td[^>]*>([\d,]+)</td>.*?<td[^>]*>([\d,]+)</td>.*?</tr>'
        matches = re.findall(row_pattern, html, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            try:
                market = match[0].strip()
                min_p = float(match[2].replace(',', ''))
                max_p = float(match[3].replace(',', ''))
                modal_p = float(match[4].replace(',', ''))
                
                if 50 < modal_p < 500000:
                    prices.append({
                        "modal": modal_p,
                        "min": min_p,
                        "max": max_p,
                        "market": market
                    })
            except:
                continue
        
        return self._calculate_stats(prices) if prices else None

    def _calculate_stats(self, prices: List[Dict]) -> Dict:
        if not prices:
            return None
            
        modal_prices = [p["modal"] for p in prices]
        min_prices = [p["min"] for p in prices]
        max_prices = [p["max"] for p in prices]
        
        lowest_idx = modal_prices.index(min(modal_prices))
        lowest_market = prices[lowest_idx]["market"]
        
        return {
            "min_price": int(min(min_prices)),
            "max_price": int(max(max_prices)),
            "modal_price": int(min(modal_prices)),
            "unit": "quintal",
            "markets_count": len(prices),
            "lowest_market": lowest_market,
            "source": "api"
        }

    async def scrape_commodity(self, commodity: Commodity) -> Dict:
        logger.info(f"Scraping {commodity.name}...")
        
        data = await self.get_agmarknet_price(commodity)
        if not data:
            data = await self.get_datagov_price(commodity)
        
        if data:
            return {
                "key": commodity.key,
                "name": commodity.name,
                "category": commodity.category,
                **data,
                "success": True
            }
        else:
            return {
                "key": commodity.key,
                "name": commodity.name,
                "category": commodity.category,
                "min_price": 0,
                "max_price": 0,
                "modal_price": 0,
                "unit": "quintal",
                "markets_count": 0,
                "success": False
            }


def get_all_commodities() -> List[Commodity]:
    commodities = []
    for category, items in COMMODITIES_CONFIG.items():
        for item in items:
            commodities.append(Commodity(
                key=item["key"],
                name=item["name"],
                api_names=item["api_names"],
                category=category
            ))
    return commodities


async def main():
    print("🚀 AgroReach India - High-Concurrency Mandi Scraper")
    print("=" * 60)
    
    commodities = get_all_commodities()
    total = len(commodities)
    print(f"Total commodities to scrape: {total}\n")
    
    results = []
    success_count = 0
    
    async with MandiPriceScraper() as scraper:
        batch_size = 5
        for i in range(0, total, batch_size):
            batch = commodities[i:i+batch_size]
            tasks = [scraper.scrape_commodity(c) for c in batch]
            batch_results = await asyncio.gather(*tasks)
            
            for result in batch_results:
                results.append(result)
                idx = len(results)
                status = "✅" if result["success"] else "❌"
                price_str = f"₹{result['modal_price']:,}" if result["success"] else "No data"
                print(f"[{idx:2d}/{total}] {status} {result['name'][:25]:<25} {price_str}")
                
                if result["success"]:
                    success_count += 1
            
            if i + batch_size < total:
                await asyncio.sleep(1)
    
    output = {
        "generated_at": datetime.now().isoformat(),
        "scraped_at": datetime.now().strftime("%d %b %Y, %I:%M %p IST"),
        "total_commodities": total,
        "successful": success_count,
        "failed": total - success_count,
        "categories": {}
    }
    
    for result in results:
        cat = result["category"]
        if cat not in output["categories"]:
            output["categories"][cat] = []
        output["categories"][cat].append(result)
    
    filename = "prices.json"
    async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(output, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 60)
    print(f"✅ Successfully scraped: {success_count}/{total}")
    print(f"📁 Saved to: {filename}")


if __name__ == "__main__":
    asyncio.run(main())

