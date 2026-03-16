import os
import asyncio
import requests
from datetime import datetime, timedelta
from supabase import create_client, Client
from shapely import wkt
from shapely.geometry import Point
import logging

# Set up logging for GitHub Actions
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
# Bounding box for East & Southern Africa (approx.)
# Format: min_longitude, min_latitude, max_longitude, max_latitude
AFRICA_BBOX = "20,-35, 42, 5" # Covers all your requested countries
COUNTRIES = ["TZ", "KE", "UG", "BW", "ZM", "ZW", "MZ", "ZA"] # ISO country codes

# API Endpoints
INATURALIST_API = "https://api.inaturalist.org/v1/observations"
EBIRD_API = "https://api.ebird.org/v2/data/obs/region/recent"
GBIF_API = "https://api.gbif.org/v1/occurrence/search"

class RealWildlifeScraper:
    def __init__(self):
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_KEY")
        self.ebird_api_key = os.environ.get("EBIRD_API_KEY") # Optional but recommended
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("❌ CRITICAL: Supabase credentials missing.")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        logging.info("🚀 Supabase client initialized.")

    def fetch_inaturalist(self):
        """Fetch research-grade observations from iNaturalist for our area."""
        sightings = []
        page = 1
        per_page = 200
        
        logging.info("🌍 Fetching from iNaturalist...")
        
        while True:
            params = {
                "verifiable": "true", # Research-grade only
                "geo": "true",
                "page": page,
                "per_page": per_page,
                "order_by": "observed_on",
                "order": "desc",
                "taxon_id": 1, # Animalia (all animals)
                "created_d1": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"), # Last 7 days
                "swlat": -35, "swlng": 20, "nelat": 5, "nelng": 42 # Bounding box
            }
            
            try:
                response = requests.get(INATURALIST_API, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                for obs in data.get('results', []):
                    if obs.get('geojson', {}).get('coordinates'):
                        # iNaturalist gives [longitude, latitude]
                        lng, lat = obs['geojson']['coordinates']
                        
                        # Get the common name or fall back to scientific name
                        species = obs['taxon']['name']
                        if obs['taxon'].get('preferred_common_name'):
                            species = obs['taxon']['preferred_common_name']
                        
                        sightings.append({
                            "source": "iNaturalist",
                            "source_url": obs['uri'],
                            "content": obs.get('description', '')[:500],
                            "extracted_species": species,
                            "confidence_score": 0.95, # Research-grade = high confidence
                            "location": f"POINT({lng} {lat})", # WKT format for PostGIS
                            "observed_at": obs.get('observed_on', datetime.now().isoformat())
                        })
                
                if len(data.get('results', [])) < per_page:
                    break
                page += 1
                
            except Exception as e:
                logging.error(f"iNaturalist API error: {e}")
                break
        
        logging.info(f"✅ Found {len(sightings)} iNaturalist sightings")
        return sightings

    def fetch_ebird(self):
        """Fetch recent bird sightings from eBird for key regions."""
        sightings = []
        
        # eBird works by region codes. Let's hit major national parks.
        hotspots = [
            "L951320", # Kruger NP
            "L275989", # Serengeti NP
            "L257851", # Ngorongoro
            "GEO-TZ", # Tanzania country
            "GEO-KE", # Kenya
            "GEO-ZA", # South Africa
        ]
        
        logging.info("🦜 Fetching from eBird...")
        
        for hotspot in hotspots:
            try:
                headers = {}
                if self.ebird_api_key:
                    headers['X-eBirdApiToken'] = self.ebird_api_key
                
                url = f"https://api.ebird.org/v2/data/obs/{hotspot}/recent"
                response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code != 200:
                    continue
                    
                data = response.json()
                for obs in data[:50]: # Limit per hotspot
                    sightings.append({
                        "source": "eBird",
                        "source_url": f"https://ebird.org/hotspot/{hotspot}",
                        "content": f"{obs.get('howMany', 1)}x {obs.get('comName', 'bird')}",
                        "extracted_species": obs.get('comName', obs.get('sciName', 'Unknown bird')),
                        "confidence_score": 0.98, # eBird data is highly verified
                        "location": None, # eBird hotspots have fixed coords we'd need to map
                        "observed_at": obs.get('obsDt', datetime.now().isoformat())
                    })
            except Exception as e:
                logging.debug(f"eBird hotspot {hotspot} error: {e}")
                continue
        
        logging.info(f"✅ Found {len(sightings)} eBird sightings")
        return sightings

    def fetch_gbif(self):
        """Fetch museum and research-grade occurrences from GBIF."""
        sightings = []
        offset = 0
        limit = 300
        
        logging.info("🏛️ Fetching from GBIF...")
        
        params = {
            "country": COUNTRIES, # List of countries
            "basisOfRecord": "HUMAN_OBSERVATION, OBSERVATION, MACHINE_OBSERVATION",
            "hasCoordinate": "true",
            "hasGeospatialIssue": "false",
            "occurrenceStatus": "present",
            "limit": limit,
            "offset": offset,
            "mediaType": "StillImage" # Only those with photos
        }
        
        try:
            while True:
                response = requests.get(GBIF_API, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                for occ in data.get('results', []):
                    if occ.get('decimalLatitude') and occ.get('decimalLongitude'):
                        species = occ.get('vernacularName') or occ.get('species') or 'Unknown'
                        
                        sightings.append({
                            "source": "GBIF",
                            "source_url": occ.get('references', 'https://gbif.org'),
                            "content": occ.get('occurrenceRemarks', '')[:500],
                            "extracted_species": species,
                            "confidence_score": 0.92,
                            "location": f"POINT({occ['decimalLongitude']} {occ['decimalLatitude']})",
                            "observed_at": occ.get('eventDate', datetime.now().isoformat())
                        })
                
                if len(data.get('results', [])) < limit:
                    break
                    
                offset += limit
                params["offset"] = offset
                
        except Exception as e:
            logging.error(f"GBIF API error: {e}")
        
        logging.info(f"✅ Found {len(sightings)} GBIF sightings")
        return sightings

    def run(self):
        """Main execution function."""
        logging.info("🚀 Starting professional wildlife data scrape...")
        
        all_sightings = []
        
        # Fetch from all sources
        all_sightings.extend(self.fetch_inaturalist())
        all_sightings.extend(self.fetch_ebird())
        all_sightings.extend(self.fetch_gbif())
        
        # Deduplicate by location + species (simple approach)
        unique_key = set()
        unique_sightings = []
        
        for s in all_sightings:
            if s['location'] is None:
                continue # Skip entries without coordinates
                
            key = f"{s['location']}_{s['extracted_species']}"
            if key not in unique_key:
                unique_key.add(key)
                unique_sightings.append(s)
        
        logging.info(f"📊 Total unique sightings to process: {len(unique_sightings)}")
        
        # Insert into Supabase
        for sighting in unique_sightings:
            try:
                # Prepare data for your existing crowdsourced_reports table
                report_data = {
                    "source": sighting['source'],
                    "source_url": sighting['source_url'],
                    "content": sighting['content'],
                    "extracted_species": sighting['extracted_species'],
                    "confidence_score": sighting['confidence_score'],
                    "location": sighting['location'], # PostGIS POINT
                }
                
                self.supabase.table("crowdsourced_reports").upsert(report_data).execute()
                logging.debug(f"✅ Inserted: {sighting['extracted_species']}")
                
            except Exception as e:
                logging.error(f"❌ Failed to insert {sighting['extracted_species']}: {e}")
        
        logging.info(f"✅ Pipeline complete! Processed {len(unique_sightings)} sightings.")
        return len(unique_sightings)

async def main():
    scraper = RealWildlifeScraper()
    count = scraper.run()
    print(f"Final count: {count} sightings added.")

if __name__ == "__main__":
    asyncio.run(main())
