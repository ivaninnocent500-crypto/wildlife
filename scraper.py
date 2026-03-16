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
AFRICA_BBOX = "20,-35,42,5" # Covers all your requested countries
COUNTRIES =["TZ", "KE", "UG", "BW", "ZM", "ZW", "MZ", "ZA", "NA"] # ISO country codes

# API Endpoints
INATURALIST_API = "https://api.inaturalist.org/v1/observations"
EBIRD_API = "https://api.ebird.org/v2/data/obs/region/recent"
GBIF_API = "https://api.gbif.org/v1/occurrence/search"

# African Safari Animals - Focus Species
SAFARI_ANIMALS = [
    # Big Five
    "lion", "elephant", "buffalo", "leopard", "rhino", "rhinoceros",
    # Other mammals
    "giraffe", "zebra", "hippo", "hippopotamus", "wildebeest", "hyena",
    "cheetah", "wild dog", "jackal", "fox", "baboon", "monkey", "ape",
    "kudu", "impala", "gazelle", "antelope", "oryx", "eland", "springbok",
    "warthog", "aardvark", "porcupine", "mongoose", "honey badger", "ratel",
    # Birds (common safari birds)
    "ostrich", "eagle", "vulture", "stork", "crane", "heron", "kingfisher",
    "hornbill", "lovebird", "parrot", "weaver", "starling", "oxpecker",
    "secretary bird", "marabou", "flamingo", "pelican", "cormorant",
    # Reptiles
    "crocodile", "tortoise", "turtle", "lizard", "chameleon", "gecko", "snake",
    "python", "cobra", "mamba", "monitor lizard", "agama"
]

# Species mapping for consistent naming in sightings table
SPECIES_MAPPING = {
    "african elephant": "elephant",
    "savanna elephant": "elephant",
    "forest elephant": "elephant",
    "african lion": "lion",
    "southern giraffe": "giraffe",
    "masai giraffe": "giraffe",
    "reticulated giraffe": "giraffe",
    "plains zebra": "zebra",
    "mountain zebra": "zebra",
    "grévy's zebra": "zebra",
    "african buffalo": "buffalo",
    "cape buffalo": "buffalo",
    "black rhino": "rhino",
    "white rhino": "rhino",
    "african leopard": "leopard",
    "common wildebeest": "wildebeest",
    "blue wildebeest": "wildebeest",
    "spotted hyena": "hyena",
    "common hippo": "hippo",
    "nile crocodile": "crocodile"
}

def is_safari_animal(species_name):
    """Check if the species is a safari animal we care about."""
    if not species_name:
        return False
    
    species_lower = species_name.lower()
    
    # Check direct match
    for animal in SAFARI_ANIMALS:
        if animal in species_lower:
            return True
    
    # Check mapping
    for key in SPECIES_MAPPING:
        if key in species_lower:
            return True
    
    return False

def normalize_species(species_name):
    """Normalize species name to our standard naming."""
    if not species_name:
        return "Unknown"
    
    species_lower = species_name.lower()
    
    # Apply mapping
    for key, value in SPECIES_MAPPING.items():
        if key in species_lower:
            return value
    
    # If no mapping, return first word capitalized
    words = species_name.split()
    return words[0].capitalize() if words else species_name

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
                    # Safely extract coordinates
                    coordinates = None
                    
                    # Method 1: geojson field
                    if obs.get('geojson') and isinstance(obs['geojson'], dict):
                        coordinates = obs['geojson'].get('coordinates')
                    
                    # Method 2: location field as fallback
                    if not coordinates and obs.get('location'):
                        try:
                            lat, lng = map(float, obs['location'].split(','))
                            coordinates = [lng, lat]
                        except:
                            pass
                    
                    if not coordinates or len(coordinates) < 2:
                        continue
                    
                    lng, lat = coordinates[0], coordinates[1]
                    
                    # Get species name safely
                    species = 'Unknown'
                    if obs.get('taxon'):
                        if obs['taxon'].get('preferred_common_name'):
                            species = obs['taxon']['preferred_common_name']
                        elif obs['taxon'].get('name'):
                            species = obs['taxon']['name']
                    
                    # Filter for safari animals only
                    if not is_safari_animal(species):
                        continue
                    
                    # Normalize species name
                    normalized_species = normalize_species(species)
                    
                    sightings.append({
                        "source": "iNaturalist",
                        "source_url": obs.get('uri', ''),
                        "content": obs.get('description', '')[:500],
                        "extracted_species": normalized_species,
                        "original_species": species, # Keep original for debugging
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
        
        logging.info(f"✅ Found {len(sightings)} iNaturalist sightings (safari animals only)")
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
        
        # Map hotspots to coordinates (simplified - center points)
        hotspot_coords = {
            "L951320": (31.5, -24.0), # Kruger approx
            "L275989": (34.8, -2.3), # Serengeti
            "L257851": (35.5, -3.2), # Ngorongoro
            "GEO-TZ": (35.0, -6.0), # Tanzania center
            "GEO-KE": (37.0, -1.0), # Kenya center
            "GEO-ZA": (25.0, -29.0), # South Africa center
        }
        
        logging.info("🦜 Fetching from eBird...")
        
        if not self.ebird_api_key:
            logging.warning("No eBird API key found. Skipping eBird data.")
            return sightings
        
        for hotspot in hotspots:
            try:
                headers = {'X-eBirdApiToken': self.ebird_api_key}
                
                url = f"https://api.ebird.org/v2/data/obs/{hotspot}/recent"
                response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code != 200:
                    continue
                    
                data = response.json()
                if not isinstance(data, list):
                    continue
                
                # Get coordinates for this hotspot
                coords = hotspot_coords.get(hotspot, (34.0, -2.0)) # Default to Serengeti area
                lng, lat = coords
                
                for obs in data[:50]: # Limit per hotspot
                    species = obs.get('comName', obs.get('sciName', ''))
                    
                    # Filter for safari birds (ostriches, eagles, vultures, etc.)
                    if not is_safari_animal(species):
                        continue
                    
                    # Add slight random variation to coordinates to spread markers
                    import random
                    var_lng = random.uniform(-0.1, 0.1)
                    var_lat = random.uniform(-0.1, 0.1)
                    
                    sightings.append({
                        "source": "eBird",
                        "source_url": f"https://ebird.org/hotspot/{hotspot}",
                        "content": f"{obs.get('howMany', 1)}x {species}",
                        "extracted_species": normalize_species(species),
                        "original_species": species,
                        "confidence_score": 0.98,
                        "location": f"POINT({lng + var_lng} {lat + var_lat})",
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
        
        # Fixed basisOfRecord parameter - using list format
        params = {
            "country": COUNTRIES,
            "basisOfRecord": ["HUMAN_OBSERVATION", "OBSERVATION", "MACHINE_OBSERVATION"],
            "hasCoordinate": "true",
            "hasGeospatialIssue": "false",
            "occurrenceStatus": "present",
            "limit": limit,
            "offset": offset,
            "mediaType": "StillImage"
        }
        
        try:
            while True:
                response = requests.get(GBIF_API, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                for occ in data.get('results', []):
                    if occ.get('decimalLatitude') and occ.get('decimalLongitude'):
                        species = occ.get('vernacularName') or occ.get('species') or ''
                        
                        # Filter for safari animals
                        if not is_safari_animal(species):
                            continue
                        
                        lng = occ['decimalLongitude']
                        lat = occ['decimalLatitude']
                        
                        # Validate coordinates are in Africa
                        if lat < -35 or lat > 5 or lng < 20 or lng > 42:
                            continue
                        
                        sightings.append({
                            "source": "GBIF",
                            "source_url": occ.get('references', 'https://gbif.org'),
                            "content": occ.get('occurrenceRemarks', '')[:500],
                            "extracted_species": normalize_species(species),
                            "original_species": species,
                            "confidence_score": 0.92,
                            "location": f"POINT({lng} {lat})",
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
        logging.info("🚀 Starting professional wildlife data scrape (African Safari Animals only)...")
        
        all_sightings = []
        
        # Fetch from all sources
        all_sightings.extend(self.fetch_inaturalist())
        all_sightings.extend(self.fetch_ebird())
        all_sightings.extend(self.fetch_gbif())
        
        # Deduplicate by location + species
        unique_key = set()
        unique_sightings = []
        
        for s in all_sightings:
            if s['location'] is None:
                continue
                
            key = f"{s['location']}_{s['extracted_species']}"
            if key not in unique_key:
                unique_key.add(key)
                unique_sightings.append(s)
        
        logging.info(f"📊 Total unique safari sightings to process: {len(unique_sightings)}")
        
        # Insert into Supabase
        inserted_count = 0
        for sighting in unique_sightings:
            try:
                # Prepare data for crowdsourced_reports table
                report_data = {
                    "source": sighting['source'],
                    "source_url": sighting['source_url'],
                    "content": sighting['content'],
                    "extracted_species": sighting['extracted_species'],
                    "confidence_score": sighting['confidence_score'],
                    "location": sighting['location'], # PostGIS POINT
                }
                
                self.supabase.table("crowdsourced_reports").upsert(report_data).execute()
                inserted_count += 1
                if inserted_count % 10 == 0:
                    logging.info(f"✅ Inserted {inserted_count}/{len(unique_sightings)} sightings...")
                
            except Exception as e:
                logging.error(f"❌ Failed to insert {sighting['extracted_species']}: {e}")
        
        logging.info(f"✅ Pipeline complete! Processed {inserted_count} safari animal sightings.")
        return inserted_count

async def main():
    scraper = RealWildlifeScraper()
    count = scraper.run()
    print(f"🎉 Final count: {count} safari animal sightings added.")
    print("🦁 Your map will now show real lions, elephants, giraffes and more!")

if __name__ == "__main__":
    asyncio.run(main())
