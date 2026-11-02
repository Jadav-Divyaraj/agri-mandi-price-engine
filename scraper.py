"""
AgroReach India - Complete Mandi Price Scraper
Uses data.gov.in API and agmarknet endpoints for accurate pricing
"""

import os
import requests
import json
import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import argparse
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class MandiPriceScraper:
    """Complete scraper for Indian mandi prices using multiple data sources"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("DATA_GOV_API_KEY", "579b464db66ec23bdd000001bf3ce4c4217e41dd6d3a8741ba5e176e")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "AgroReach India/1.0 (https://agroreach.in)",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://agmarknet.gov.in/",
        })
        
        # API endpoints
        self.endpoints = {
            "data_gov": "https://api.data.gov.in/resource/",
            "agmarknet_api": "https://api.agmarket.gov.in/v1/",
            "agmarknet_legacy": "https://agmarknet.gov.in/api/PriceData",
        }
    
    def get_commodity_data_gov(self, commodity: str, state: str = None) -> Optional[Dict]:
        """Fetch price data from data.gov.in API"""
        try:
            # data.gov.in resource IDs for market prices
            resource_ids = [
                "9ef84268-d588-465a-a308-a864a43d0070",  # Market prices
                "de3dbf1d-2a6d-46f0-a4f1-0f4b301b3de4",  # Commodity prices
            ]
            
            for resource_id in resource_ids:
                params = {
                    "api-key": self.api_key,
                    "format": "json",
                    "limit": "50",
                }
                
                # Add filter if provided
                if commodity:
                    params["filters[commodity]"] = commodity
                if state:
                    params["filters[state]"] = state
                
                response = self.session.get(
                    f"{self.endpoints['data_gov']}{resource_id}",
                    params=params,
                    timeout=15
                )
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data.get('records'):
                            return self._process_data_gov_response(data['records'])
                    except:
                        continue
                        
        except Exception as e:
            logger.debug(f"data.gov.in error for {commodity}: {e}")
        
        return None
    
    def get_commodity_agmarknet(self, commodity: str, date: str = None) -> Optional[Dict]:
        """Fetch price data from agmarknet API"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        try:
            # Try multiple parameter formats
            param_formats = [
                {"commodity": commodity, "date": date},
                {"q": commodity, "dt": date},
                {"name": commodity, "date": date},
            ]
            
            for params in param_formats:
                response = self.session.get(
                    self.endpoints['agmarknet_legacy'],
                    params=params,
                    timeout=15
                )
                
                if response.status_code == 200:
                    # Try to parse JSON
                    try:
                        data = response.json()
                        if data:
                            return self._process_agmarknet_response(data, commodity)
                    except:
                        # If not JSON, try to extract from HTML
                        if response.text and ('price' in response.text.lower() or 'modal' in response.text.lower()):
                            result = self._extract_from_html(response.text, commodity)
                            if result:
                                return result
                        
        except Exception as e:
            logger.debug(f"agmarknet API error for {commodity}: {e}")
        
        return None
    
    def _process_data_gov_response(self, records: List) -> Dict:
        """Process data.gov.in API response"""
        prices = []
        for record in records:
            try:
                # Try different field names
                modal_price = (record.get('modal_price') or 
                              record.get('price') or 
                              record.get('avg_price') or 
                              record.get('modal'))
                
                if modal_price:
                    # Convert to float if string
                    if isinstance(modal_price, str):
                        modal_price = float(modal_price.replace(',', ''))
                    
                    min_price = record.get('min_price', modal_price)
                    max_price = record.get('max_price', modal_price)
                    
                    if isinstance(min_price, str):
                        min_price = float(min_price.replace(',', ''))
                    if isinstance(max_price, str):
                        max_price = float(max_price.replace(',', ''))
                    
                    prices.append({
                        "market": record.get('market', record.get('market_name', 'Unknown')),
                        "state": record.get('state', record.get('state_name', 'Unknown')),
                        "district": record.get('district', 'Unknown'),
                        "min_price": float(min_price),
                        "max_price": float(max_price),
                        "modal_price": float(modal_price),
                        "arrivals": record.get('arrivals', record.get('arrival', 0))
                    })
            except (ValueError, TypeError, KeyError) as e:
                continue
        
        if prices:
            return self._calculate_price_stats(prices)
        return None
    
    def _process_agmarknet_response(self, data: Dict, commodity: str) -> Optional[Dict]:
        """Process agmarknet API response"""
        if isinstance(data, dict):
            # Try different data structures
            if 'prices' in data:
                return self._calculate_price_stats(data['prices'])
            elif 'data' in data:
                return self._calculate_price_stats(data['data'])
            elif 'records' in data:
                return self._calculate_price_stats(data['records'])
            else:
                # If direct price data
                modal = data.get('modal_price') or data.get('price') or data.get('modal')
                if modal:
                    return {
                        "min_price": int(data.get('min_price', modal)),
                        "max_price": int(data.get('max_price', modal)),
                        "modal_price": int(modal),
                        "unit": "quintal",
                        "markets_count": 1
                    }
        return None
    
    def _extract_from_html(self, html: str, commodity: str) -> Optional[Dict]:
        """Extract price data from HTML response"""
        # Look for price patterns in HTML
        prices = []
        
        # Pattern 1: Table cells with prices
        table_pattern = r'<td[^>]*>([\d,]+)\s*<\/td>\s*<td[^>]*>quintal'
        matches = re.findall(table_pattern, html, re.IGNORECASE)
        for match in matches:
            try:
                price = float(match.replace(',', ''))
                if 100 < price < 200000:  # Reasonable price range
                    prices.append(price)
            except:
                continue
        
        # Pattern 2: JSON-like structures
        json_pattern = r'"price"\s*:\s*([\d.]+)'
        matches = re.findall(json_pattern, html)
        for match in matches:
            try:
                price = float(match)
                if 100 < price < 200000:
                    prices.append(price)
            except:
                continue
        
        # Pattern 3: ₹ symbol followed by number
        rupee_pattern = r'[₹]\s*([\d,]+)'
        matches = re.findall(rupee_pattern, html)
        for match in matches:
            try:
                price = float(match.replace(',', ''))
                if 100 < price < 200000:
                    prices.append(price)
            except:
                continue
        
        if prices:
            return {
                "min_price": int(min(prices)),
                "max_price": int(max(prices)),
                "modal_price": int(min(prices)),  # Use lowest as modal
                "unit": "quintal",
                "source": "html_extract",
                "markets_count": len(prices)
            }
        return None
    
    def _calculate_price_stats(self, prices: List[Dict]) -> Dict:
        """Calculate min, max, and modal prices from price list"""
        if not prices:
            return None
        
        modal_prices = []
        min_prices = []
        max_prices = []
        
        for p in prices:
            # Handle both dict and numeric values
            if isinstance(p, dict):
                modal = p.get('modal_price') or p.get('price') or p.get('modal')
                min_p = p.get('min_price', modal)
                max_p = p.get('max_price', modal)
            else:
                modal = p
                min_p = p
                max_p = p
            
            if modal and float(modal) > 0:
                try:
                    modal_prices.append(float(modal))
                    if min_p:
                        min_prices.append(float(min_p))
                    if max_p:
                        max_prices.append(float(max_p))
                except (ValueError, TypeError):
                    continue
        
        if not modal_prices:
            return None
        
        # Find lowest modal price (best deal for buyer)
        lowest_modal = min(modal_prices)
        
        # Find market with lowest price if available
        lowest_market = None
        for p in prices:
            if isinstance(p, dict):
                modal = p.get('modal_price') or p.get('price') or p.get('modal')
                if modal and float(modal) == lowest_modal:
                    lowest_market = p.get('market', p.get('market_name', 'Unknown'))
                    break
        
        return {
            "min_price": int(min(min_prices)) if min_prices else int(lowest_modal),
            "max_price": int(max(max_prices)) if max_prices else int(lowest_modal),
            "modal_price": int(lowest_modal),
            "lowest_market": lowest_market,
            "markets_count": len(modal_prices),
            "unit": "quintal"
        }

# Complete commodity mapping matching your website
COMMODITIES = {
    "spices": [
        {"key": "cumin", "name": "Cumin Seeds", "api_names": ["Jeera", "Cumin"]},
        {"key": "turmeric", "name": "Turmeric", "api_names": ["Turmeric"]},
        {"key": "chilli", "name": "Red Chilli", "api_names": ["Dry Chillies", "Red Chilli"]},
        {"key": "coriander", "name": "Coriander Seeds", "api_names": ["Coriander"]},
        {"key": "pepper", "name": "Black Pepper", "api_names": ["Black Pepper"]},
        {"key": "cardamom", "name": "Cardamom", "api_names": ["Cardamom"]},
        {"key": "ginger", "name": "Ginger (Dry)", "api_names": ["Ginger"]},
        {"key": "garlic", "name": "Garlic", "api_names": ["Garlic"]},
        {"key": "mustard", "name": "Mustard Seeds", "api_names": ["Mustard"]},
        {"key": "fenugreek", "name": "Fenugreek", "api_names": ["Fenugreek", "Methi"]},
        {"key": "fennel", "name": "Fennel Seeds", "api_names": ["Fennel", "Saunf"]},
        {"key": "ajwain", "name": "Ajwain", "api_names": ["Ajwain", "Carom"]},
    ],
    "fruits": [
        {"key": "mango", "name": "Alphonso Mango", "api_names": ["Mango"]},
        {"key": "pomegranate", "name": "Pomegranate", "api_names": ["Pomegranate"]},
        {"key": "grapes", "name": "Grapes", "api_names": ["Grapes"]},
        {"key": "banana", "name": "Banana", "api_names": ["Banana"]},
        {"key": "apple", "name": "Apple", "api_names": ["Apple"]},
        {"key": "coconut", "name": "Coconut", "api_names": ["Coconut"]},
        {"key": "orange", "name": "Orange", "api_names": ["Orange"]},
        {"key": "papaya", "name": "Papaya", "api_names": ["Papaya"]},
        {"key": "guava", "name": "Guava", "api_names": ["Guava"]},
        {"key": "watermelon", "name": "Watermelon", "api_names": ["Watermelon"]},
    ],
    "vegetables": [
        {"key": "onion", "name": "Onion", "api_names": ["Onion"]},
        {"key": "potato", "name": "Potato", "api_names": ["Potato"]},
        {"key": "tomato", "name": "Tomato", "api_names": ["Tomato"]},
        {"key": "greenchilli", "name": "Green Chilli", "api_names": ["Green Chilli"]},
        {"key": "cauliflower", "name": "Cauliflower", "api_names": ["Cauliflower"]},
        {"key": "carrot", "name": "Carrot", "api_names": ["Carrot"]},
        {"key": "capsicum", "name": "Capsicum", "api_names": ["Capsicum"]},
        {"key": "brinjal", "name": "Brinjal", "api_names": ["Brinjal"]},
        {"key": "ladyfinger", "name": "Lady Finger", "api_names": ["Bhindi", "Lady Finger"]},
    ],
    "grains": [
        {"key": "basmati", "name": "Basmati Rice", "api_names": ["Basmati", "Rice"]},
        {"key": "wheat", "name": "Wheat", "api_names": ["Wheat"]},
        {"key": "maize", "name": "Maize", "api_names": ["Maize"]},
        {"key": "chana", "name": "Chana (Gram)", "api_names": ["Gram", "Chana"]},
        {"key": "soybean", "name": "Soybean", "api_names": ["Soybean"]},
        {"key": "tur", "name": "Tur Dal", "api_names": ["Tur", "Arhar"]},
        {"key": "moong", "name": "Moong Dal", "api_names": ["Moong"]},
        {"key": "urad", "name": "Urad Dal", "api_names": ["Urad"]},
        {"key": "bajra", "name": "Bajra", "api_names": ["Bajra"]},
        {"key": "jowar", "name": "Jowar", "api_names": ["Jowar"]},
    ],
    "dryfruits": [
        {"key": "cashew", "name": "Cashew W320", "api_names": ["Cashew"]},
        {"key": "almonds", "name": "Almonds", "api_names": ["Almond"]},
        {"key": "raisins", "name": "Raisins", "api_names": ["Raisins", "Dry Grapes"]},
        {"key": "walnut", "name": "Walnut", "api_names": ["Walnut"]},
        {"key": "dates", "name": "Dates", "api_names": ["Dates"]},
    ],
    "oils": [
        {"key": "groundnut", "name": "Groundnut", "api_names": ["Groundnut"]},
        {"key": "sesame", "name": "Sesame Seeds", "api_names": ["Sesame", "Til"]},
        {"key": "castorseed", "name": "Castor Seed", "api_names": ["Castor"]},
        {"key": "sunflowerseed", "name": "Sunflower Seed", "api_names": ["Sunflower"]},
    ],
}

def scrape_all_prices(api_key: str = None, output_file: str = "prices.json"):
    """Scrape prices for all commodities"""
    
    print("="*70)
    print("AgroReach India - Complete Mandi Price Scraper")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    scraper = MandiPriceScraper(api_key)
    
    # Prepare output
    output = {
        "generated_at": datetime.now().isoformat(),
        "scraped_at": datetime.now().strftime("%d %b %Y %H:%M:%S IST"),
        "source": "data.gov.in API + Agmarknet",
        "disclaimer": "Prices are the lowest modal price across all Indian markets",
        "categories": {}
    }
    
    total_commodities = sum(len(items) for items in COMMODITIES.values())
    scraped_count = 0
    failed_count = 0
    
    for category, items in COMMODITIES.items():
        print(f"\n📁 Category: {category.upper()}")
        output["categories"][category] = []
        
        for idx, commodity in enumerate(items, 1):
            name = commodity["name"]
            api_names = commodity["api_names"]
            
            print(f"  [{idx}/{len(items)}] {name}...", end=" ", flush=True)
            
            price_data = None
            
            # Try each API name
            for api_name in api_names:
                # Try agmarknet API first
                price_data = scraper.get_commodity_agmarknet(api_name)
                if price_data and price_data.get('modal_price', 0) > 0:
                    print(f"✓ ₹{price_data['modal_price']:,} (agmarknet)")
                    break
                
                # Try data.gov.in as fallback
                price_data = scraper.get_commodity_data_gov(api_name)
                if price_data and price_data.get('modal_price', 0) > 0:
                    print(f"✓ ₹{price_data['modal_price']:,} (data.gov.in)")
                    break
            
            if price_data and price_data.get('modal_price', 0) > 0:
                scraped_count += 1
                entry = {
                    **commodity,
                    "category": category,
                    "min_price": price_data.get("min_price", 0),
                    "max_price": price_data.get("max_price", 0),
                    "modal_price": price_data["modal_price"],
                    "unit": price_data.get("unit", "quintal"),
                    "lowest_market": price_data.get("lowest_market"),
                    "markets_count": price_data.get("markets_count", 1)
                }
            else:
                failed_count += 1
                print("❌ No data")
                entry = {
                    **commodity,
                    "category": category,
                    "min_price": 0,
                    "max_price": 0,
                    "modal_price": 0,
                    "unit": "quintal"
                }
            
            output["categories"][category].append(entry)
            time.sleep(0.5)  # Respect rate limits
    
    # Save output
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    # Summary
    print("\n" + "="*70)
    print("SCRAPING COMPLETE")
    print("="*70)
    print(f"✅ Successfully scraped: {scraped_count}/{total_commodities}")
    print(f"❌ Failed: {failed_count}")
    print(f"📁 Output saved: {output_file}")
    print("="*70)
    
    # Show sample of scraped data
    if scraped_count > 0:
        print("\n📊 Sample Prices:")
        for category, items in output["categories"].items():
            for item in items[:3]:  # Show first 3 per category
                if item['modal_price'] > 0:
                    print(f"  • {item['name']}: ₹{item['modal_price']:,} per {item['unit']}")
            break  # Only show first category
    
    return output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgroReach Mandi Price Scraper")
    parser.add_argument("--api-key", help="data.gov.in API key", default="579b464db66ec23bdd000001bf3ce4c4217e41dd6d3a8741ba5e176e")
    parser.add_argument("--output", default="prices.json", help="Output file name")
    
    args = parser.parse_args()
    scrape_all_prices(args.api_key, args.output)