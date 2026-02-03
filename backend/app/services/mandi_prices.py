"""
Mandi Price Integration Service.

Connects to the Open Government Data (OGD) Platform India (data.gov.in) 
to fetch current market prices for agricultural commodities.
"""

import requests
import logging
from typing import List, Dict, Optional
from app.config.settings import settings

logger = logging.getLogger(__name__)

class MandiPriceService:
    """
    Service for fetching commodity price data from AGMARKNET / OGD India.
    
    API Documentation: https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi
    """
    
    BASE_URL = "https://api.data.gov.in/resource/9ef2731d-91d2-4581-adbc-a24ad7373c04"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "OGD_INDIA_API_KEY", None)
        
    def get_latest_prices(self, commodity: Optional[str] = None, state: Optional[str] = None) -> List[Dict]:
        """
        Fetch latest mandi prices from OGD India.
        """
        if not self.api_key:
            logger.warning("OGD_INDIA_API_KEY not configured. Returning mock/empty data.")
            return self._get_mock_data()
            
        params = {
            "api-key": self.api_key,
            "format": "json",
            "limit": 10
        }
        
        if commodity:
            params["filters[commodity]"] = commodity
        if state:
            params["filters[state]"] = state
            
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("records", [])
        except Exception as e:
            logger.error(f"Failed to fetch Mandi prices: {e}")
            return self._get_mock_data()
            
    def _get_mock_data(self) -> List[Dict]:
        """Return fallback data if API is unavailable or unconfigured."""
        return [
            {"commodity": "Sugar", "market": "Delhi", "state": "Delhi", "max_price": "4200", "modal_price": "4100", "date": "2026-02-03"},
            {"commodity": "Rice", "market": "Karnal", "state": "Haryana", "max_price": "3800", "modal_price": "3600", "date": "2026-02-03"},
            {"commodity": "Salt", "market": "Mumbai", "state": "Maharashtra", "max_price": "2500", "modal_price": "2400", "date": "2026-02-03"}
        ]
