import os
import requests
from datetime import datetime, timedelta
from supabase import create_client, Client
import logging
import uuid
import random

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class RealWildlifeScraper:
    def __init__(self):
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("❌ CRITICAL: Supabase credentials missing.")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        logging.info("🚀 Supabase client initialized.")

    def fetch_inaturalist(self):
        """Fetch from iNaturalist."""
        sightings = []
        
        logging.info("🌍 Fetching from iNaturalist...")
        
        # Safari animal scientific names
        safari_species = {
            "lion": "Panthera leo",
            "elephant": "Loxodonta africana",
            "giraffe": "Giraffa camelopardalis",
            "zebra": "Equus quagga",
            "leopard": "Panthera pardus",
            "cheetah": "Acinonyx jubatus",
            "buffalo": "Syncerus caffer",
            "rhino": "Ceratotherium simum",
            "hippo": "Hippopotamus amphibius",
            "wildebeest": "Connochaetes taurinus"
        }
        
        for common_name, scientific_name in safari_species.items():
            try:
                params = {
                    "verifiable": "true",
                    "geo": "true",
                    "per_page": 20,
                    "taxon_name": scientific_name,
                    "swlat": -35, "swlng": 10,
                    "nelat": 10, "nelng": 45,
                    "order_by": "observed_on",
                    "order": "desc"
                }
                
                response = requests.get(
                    "https://api.inaturalist.org/v1/observations",
                    params=params,
                    timeout=15
                )
                response.raise_for_status()
                data = response.json()
                
                for obs in data.get('results', []):
                    if obs.get('geojson') and obs['geojson'].get('coordinates'):
                        lng, lat = obs['geojson']['coordinates']
                        
                        # Generate random environmental data
                        ndvi = round(random.uniform(0.3, 0.8), 2)
                        water_dist = round(random.uniform(50, 500), 1)
                        
                        sightings.append({
                            "species_name": common_name.capitalize(),
                            "location": f"POINT({lng} {lat})",
                            "ndvi_value": ndvi,
                            "distance_to_water": water_dist,
                            "source": "iNaturalist",
                            "source_url": obs.get('uri', ''),
                            "confidence_score": 0.95,
                            "observed_at": obs.get('observed_on', datetime.now().isoformat())
                        })
                        
            except Exception as e:
                logging.error(f"Error fetching {common_name}: {e}")
                continue
        
        logging.info(f"✅ Found {len(sightings)} iNaturalist sightings")
        return sightings

    def fetch_test_data(self):
        """Generate test data with all required fields."""
        logging.info("🧪 Generating test data...")
        
        test_sightings = [
            {
                "species_name": "Lion",
                "location": "POINT(34.8 -2.3)", # Serengeti
                "ndvi_value": 0.45,
                "distance_to_water": 300,
                "source": "Test",
                "source_url": f"https://example.com/lion/{uuid.uuid4()}",
                "confidence_score": 0.95,
                "observed_at": datetime.now().isoformat()
            },
            {
                "species_name": "Elephant",
                "location": "POINT(31.5 -24.0)", # Kruger
                "ndvi_value": 0.65,
                "distance_to_water": 150,
                "source": "Test",
                "source_url": f"https://example.com/elephant/{uuid.uuid4()}",
                "confidence_score": 0.95,
                "observed_at": datetime.now().isoformat()
            },
            {
                "species_name": "Giraffe",
                "location": "POINT(35.5 -3.2)", # Ngorongoro
                "ndvi_value": 0.55,
                "distance_to_water": 200,
                "source": "Test",
                "source_url": f"https://example.com/giraffe/{uuid.uuid4()}",
                "confidence_score": 0.95,
                "observed_at": datetime.now().isoformat()
            },
            {
                "species_name": "Leopard",
                "location": "POINT(34.5 -2.5)",
                "ndvi_value": 0.50,
                "distance_to_water": 250,
                "source": "Test",
                "source_url": f"https://example.com/leopard/{uuid.uuid4()}",
                "confidence_score": 0.95,
                "observed_at": datetime.now().isoformat()
            },
            {
                "species_name": "Cheetah",
                "location": "POINT(35.0 -3.0)",
                "ndvi_value": 0.40,
                "distance_to_water": 400,
                "source": "Test",
                "source_url": f"https://example.com/cheetah/{uuid.uuid4()}",
                "confidence_score": 0.95,
                "observed_at": datetime.now().isoformat()
            },
            {
                "species_name": "Zebra",
                "location": "POINT(34.9 -2.8)",
                "ndvi_value": 0.52,
                "distance_to_water": 180,
                "source": "Test",
                "source_url": f"https://example.com/zebra/{uuid.uuid4()}",
                "confidence_score": 0.95,
                "observed_at": datetime.now().isoformat()
            }
        ]
        
        logging.info(f"✅ Generated {len(test_sightings)} test sightings")
        return test_sightings

    def run(self):
        """Main execution - inserts directly into sightings table."""
        logging.info("🚀 Starting wildlife data scrape...")
        
        all_sightings = []
        
        # Get real data from iNaturalist
        # all_sightings.extend(self.fetch_inaturalist())
        
        # Use test data for now
        all_sightings.extend(self.fetch_test_data())
        
        # Insert directly into sightings table
        inserted_count = 0
        for sighting in all_sightings:
            try:
                # Check if this sighting already exists (avoid duplicates)
                existing = self.supabase.table("sightings")\
                    .select("*")\
                    .eq("location", sighting['location'])\
                    .eq("species_name", sighting['species_name'])\
                    .execute()
                
                if not existing.data:
                    # Insert directly into sightings
                    data = {
                        "species_name": sighting['species_name'],
                        "location": sighting['location'],
                        "ndvi_value": sighting['ndvi_value'],
                        "distance_to_water": sighting['distance_to_water'],
                        "source": sighting['source'],
                        "confidence": sighting['confidence_score']
                    }
                    
                    self.supabase.table("sightings").insert(data).execute()
                    inserted_count += 1
                    logging.info(f"✅ Inserted: {sighting['species_name']}")
                else:
                    logging.info(f"⏭️ Skipped duplicate: {sighting['species_name']}")
                
            except Exception as e:
                logging.error(f"❌ Failed to insert {sighting['species_name']}: {e}")
        
        logging.info(f"✅ Done! Inserted {inserted_count} new sightings")
        return inserted_count

def main():
    scraper = RealWildlifeScraper()
    count = scraper.run()
    print(f"🎉 Added {count} new safari animal sightings directly to sightings table!")

if __name__ == "__main__":
    main()
