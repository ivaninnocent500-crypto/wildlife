import os
import asyncio
import requests
from datetime import datetime, timedelta
from supabase import create_client, Client
import logging
import random

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
COUNTRIES = ["TZ", "KE", "UG", "BW", "ZM", "ZW", "MZ", "ZA", "NA"]

# API Endpoints
INATURALIST_API = "https://api.inaturalist.org/v1/observations"
GBIF_API = "https://api.gbif.org/v1/occurrence/search"

# African Safari Animals
SAFARI_ANIMALS = [
    "lion", "elephant", "buffalo", "leopard", "rhino", "giraffe", "zebra", 
    "hippo", "wildebeest", "hyena", "cheetah", "ostrich", "crocodile"
]

SPECIES_MAPPING = {
    "african elephant": "elephant", "african lion": "lion", "southern giraffe": "giraffe",
    "plains zebra": "zebra", "african buffalo": "buffalo", "black rhino": "rhino",
    "white rhino": "rhino", "common wildebeest": "wildebeest", "spotted hyena": "hyena",
    "nile crocodile": "crocodile"
}

def is_safari_animal(species_name):
    if not species_name:
        return False
    species_lower = species_name.lower()
    for animal in SAFARI_ANIMALS:
        if animal in species_lower:
            return True
    for key in SPECIES_MAPPING:
        if key in species_lower:
            return True
    return False

def normalize_species(species_name):
    if not species_name:
        return "Unknown"
    species_lower = species_name.lower()
    for key, value in SPECIES_MAPPING.items():
        if key in species_lower:
            return value
    words = species_name.split()
    return words[0].capitalize() if words else species_name

class RealWildlifeScraper:
    def __init__(self):
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("❌ CRITICAL: Supabase credentials missing.")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        logging.info("🚀 Supabase client initialized.")

    def fetch_inaturalist(self):
        """Fetch ONLY 1 page of recent safari sightings (fast!)."""
        sightings = []
        
        logging.info("🌍 Fetching from iNaturalist (1 page only)...")
        
        params = {
            "verifiable": "true",
            "geo": "true",
            "per_page": 50, # Small page size
            "order_by": "observed_on",
            "order": "desc",
            "taxon_id": 1,
            "created_d1": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"), # Last 3 days only
            "swlat": -35, "swlng": 20, "nelat": 5, "nelng": 42
        }
        
        try:
            response = requests.get(INATURALIST_API, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            for obs in data.get('results', []):
                # Extract coordinates
                coordinates = None
                if obs.get('geojson') and isinstance(obs['geojson'], dict):
                    coordinates = obs['geojson'].get('coordinates')
                
                if not coordinates and obs.get('location'):
                    try:
                        lat, lng = map(float, obs['location'].split(','))
                        coordinates = [lng, lat]
                    except:
                        pass
                
                if not coordinates or len(coordinates) < 2:
                    continue
                
                lng, lat = coordinates[0], coordinates[1]
                
                # Get species
                species = 'Unknown'
                if obs.get('taxon'):
                    if obs['taxon'].get('preferred_common_name'):
                        species = obs['taxon']['preferred_common_name']
                    elif obs['taxon'].get('name'):
                        species = obs['taxon']['name']
                
                if not is_safari_animal(species):
                    continue
                
                sightings.append({
                    "source": "iNaturalist",
                    "source_url": obs.get('uri', ''),
                    "content": obs.get('description', '')[:200],
                    "extracted_species": normalize_species(species),
                    "confidence_score": 0.95,
                    "location": f"POINT({lng} {lat})",
                })
            
        except Exception as e:
            logging.error(f"iNaturalist API error: {e}")
        
        logging.info(f"✅ Found {len(sightings)} iNaturalist sightings")
        return sightings

    def fetch_gbif(self):
        """Fetch ONLY 1 page of GBIF data."""
        sightings = []
        
        logging.info("🏛️ Fetching from GBIF (1 page only)...")
        
        params = {
            "country": COUNTRIES,
            "basisOfRecord": "HUMAN_OBSERVATION,OBSERVATION",
            "hasCoordinate": "true",
            "limit": 100, # Small limit
            "mediaType": "StillImage"
        }
        
        try:
            response = requests.get(GBIF_API, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            for occ in data.get('results', [])[:50]: # Take first 50
                if occ.get('decimalLatitude') and occ.get('decimalLongitude'):
                    species = occ.get('vernacularName') or occ.get('species') or ''
                    
                    if not is_safari_animal(species):
                        continue
                    
                    lng = occ['decimalLongitude']
                    lat = occ['decimalLatitude']
                    
                    sightings.append({
                        "source": "GBIF",
                        "source_url": occ.get('references', 'https://gbif.org'),
                        "content": occ.get('occurrenceRemarks', '')[:200],
                        "extracted_species": normalize_species(species),
                        "confidence_score": 0.92,
                        "location": f"POINT({lng} {lat})",
                    })
                    
        except Exception as e:
            logging.error(f"GBIF API error: {e}")
        
        logging.info(f"✅ Found {len(sightings)} GBIF sightings")
        return sightings

    def run(self):
        """Fast execution - completes in minutes not hours."""
        logging.info("🚀 Starting FAST wildlife data scrape...")
        
        all_sightings = []
        all_sightings.extend(self.fetch_inaturalist())
        all_sightings.extend(self.fetch_gbif())
        
        # Insert immediately - no heavy deduplication
        inserted_count = 0
        for sighting in all_sightings[:100]: # Max 100 total
            try:
                report_data = {
                    "source": sighting['source'],
                    "source_url": sighting['source_url'],
                    "content": sighting['content'],
                    "extracted_species": sighting['extracted_species'],
                    "confidence_score": sighting['confidence_score'],
                    "location": sighting['location'],
                }
                
                self.supabase.table("crowdsourced_reports").upsert(report_data).execute()
                inserted_count += 1
                logging.info(f"✅ Inserted: {sighting['extracted_species']}")
                
            except Exception as e:
                logging.error(f"❌ Failed: {e}")
        
        logging.info(f"✅ Done! Processed {inserted_count} sightings in record time!")
        return inserted_count

async def main():
    scraper = RealWildlifeScraper()
    count = scraper.run()
    print(f"🎉 Added {count} safari animal sightings!")

if __name__ == "__main__":
    asyncio.run(main())
