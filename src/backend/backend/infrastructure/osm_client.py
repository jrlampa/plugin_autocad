import requests
from typing import Callable, Any
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class OsmClient:
    """
    Handles all external communication with the Overpass API.
    Single Responsibility: Networking and raw data retrieval.
    """
    
    OVERPASS_URL = "https://overpass-api.de/api/interpreter"

    @staticmethod
    def fetch_overpass_data(lat: float, lon: float, radius: float, check_cancel: Callable = None) -> dict:
        """
        Fetches raw OSM data using the Overpass API.
        """
        # Overpass QL query: Fetch all ways and nodes within radius
        delta = radius / 111320.0  # Approximate degrees per meter
        s, w, n, e = lat - delta, lon - delta, lat + delta, lon + delta
        
        query = f"""
        [out:json][timeout:30];
        (
          way["highway"]({s},{w},{n},{e});
          node["highway"~"street_light|bus_stop|traffic_signals|crossing"]({s},{w},{n},{e});
          node["power"="pole"]({s},{w},{n},{e});
          node["amenity"~"fire_hydrant|bench|waste_basket"]({s},{w},{n},{e});
          node["man_made"="manhole"]({s},{w},{n},{e});
          node["natural"="tree"]({s},{w},{n},{e});
        );
        out body;
        >;
        out skel qt;
        """
        
        if check_cancel: check_cancel()
        
        logger.info("overpass_fetch_start", lat=lat, lon=lon, radius=radius)
        
        headers = {
            "User-Agent": "sisRUA Engineering Plugin (https://sisrua.com)",
            "Accept-Encoding": "gzip, deflate"
        }
        
        try:
            # Polite retry strategy
            for attempt in range(3):
                try:
                    response = requests.post(
                        OsmClient.OVERPASS_URL, 
                        data={"data": query}, 
                        headers=headers,
                        timeout=30
                    )
                    response.raise_for_status()
                    break
                except requests.RequestException as e:
                    if attempt == 2: raise
                    logger.warning("overpass_retry", attempt=attempt+1, error=str(e))
                    import time
                    time.sleep(2 * (attempt + 1))
            
            if check_cancel: check_cancel()
            return response.json()
            
        except requests.HTTPError as h:
            if h.response.status_code == 429:
                logger.error("overpass_rate_limited")
                raise Exception("Overpass API rate limited. Please wait and try again.")
            raise
