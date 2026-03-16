import os
import requests
from datetime import datetime, timedelta
from supabase import create_client, Client
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
COUNTRIES = "TZ,KE,UG,BW,ZW,ZA,NA,MZ,ZM" # Comma-separated string, not list

class RealWildlifeScraper:
    def __init__(self):
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("❌ CRITICAL: Supabase credentials missing.")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        logging.info("🚀 Supabase client initialized.")

    def fetch_inaturalist(self):
        """Fetch from iNaturalist with working parameters."""
        sightings = []
        
        logging.info("🌍 Fetching from iNaturalist...")
        
        # FIXED: Use simpler parameters that definitely work
        params = {
            "verifiable": "true",
            "geo": "true",
            "per_page": 100,
            "order_by": "observed_on",
            "taxon_id": "mammalia,bird", # Focus on mammals and birds
            "swlat": -35, "swlng": 20, 
            "nelat": 5, "nelng": 42,
            "popular": "true" # Get popular observations
        }
        
        try:
            response = requests.get(
                "https://api.inaturalist.org/v1/observations", 
                params=params, 
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            for obs in data.get('results', []):
                # Get coordinates
                if obs.get('geojson') and obs['geojson'].get('coordinates'):
                    lng, lat = obs['geojson']['coordinates']
                    
                    # Get species name
                    species = "Unknown"
                    if obs.get('taxon'):
                        species = obs['taxon'].get('name', 'Unknown')
                    
                    # Map common safari animals
                    species_lower = species.lower()
                    if any(animal in species_lower for animal in ["lion", "elephant", "giraffe", "zebra", "buffalo", "rhino", "leopard", "cheetah", "hippo", "wildebeest"]):
                        sightings.append({
                            "source": "iNaturalist",
                            "source_url": obs.get('uri', ''),
                            "content": obs.get('description', '')[:200],
                            "extracted_species": species.split()[-1].capitalize(),
                            "confidence_score": 0.95,
                            "location": f"POINT({lng} {lat})",
                        })
            
        except Exception as e:
            logging.error(f"iNaturalist error: {e}")
        
        logging.info(f"✅ Found {len(sightings)} iNaturalist sightings")
        return sightings

    def fetch_gbif(self):
        """Fetch from GBIF with working parameters."""
        sightings = []
        
        logging.info("🏛️ Fetching from GBIF...")
        
        # FIXED: Use proper GBIF parameters
        params = {
            "country": COUNTRIES,
            "basisOfRecord": "HUMAN_OBSERVATION",
            "hasCoordinate": "true",
            "limit": 100,
            "taxonKey": [
                5242590, # Lion
                5219451, # Elephant
                5220147, # Giraffe
                5220165, # Zebra
                5429124, # Buffalo
                5429125, # Rhino
                5429126, # Leopard
                5429127, # Cheetah
            ]
        }
        
        try:
            response = requests.get(
                "https://api.gbif.org/v1/occurrence/search",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            for occ in data.get('results', []):
                if occ.get('decimalLatitude') and occ.get('decimalLongitude'):
                    species = occ.get('species', 'Unknown')
                    lng = occ['decimalLongitude']
                    lat = occ['decimalLatitude']
                    
                    sightings.append({
                        "source": "GBIF",
                        "source_url": occ.get('references', ''),
                        "content": occ.get('occurrenceRemarks', '')[:200],
                        "extracted_species": species.split()[-1].capitalize(),
                        "confidence_score": 0.92,
                        "location": f"POINT({lng} {lat})",
                    })
                    
        except Exception as e:
            logging.error(f"GBIF error: {e}")
        
        logging.info(f"✅ Found {len(sightings)} GBIF sightings")
        return sightings

    def run(self):
        """Main execution."""
        logging.info("🚀 Starting wildlife data scrape...")
        
        all_sightings = []
        all_sightings.extend(self.fetch_inaturalist())
        all_sightings.extend(self.fetch_gbif())
        
        # Insert into Supabase
        inserted_count = 0
        for sighting in all_sightings:
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
        
        logging.info(f"✅ Done! Processed {inserted_count} sightings")
        return inserted_count

def main():
    scraper = RealWildlifeScraper()
    count = scraper.run()
    print(f"🎉 Added {count} safari animal sightings!")

if __name__ == "__main__":
    main()
