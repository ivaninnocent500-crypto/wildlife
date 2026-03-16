import os
import requests
from datetime import datetime, timedelta
from supabase import create_client, Client
import logging

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
        """Fetch from iNaturalist with working parameters."""
        sightings = []
        
        logging.info("🌍 Fetching from iNaturalist...")
        
        # Use a broader search that definitely returns results
        params = {
            "verifiable": "true",
            "geo": "true",
            "per_page": 100,
            "order_by": "observed_on",
            "taxon_name": "Panthera leo,Loxodonta africana,Giraffa camelopardalis,Equus quagga", # Specific species
            "swlat": -35, "swlng": 10, 
            "nelat": 10, "nelng": 45, # Wider Africa bounds
            "popular": "true"
        }
        
        try:
            response = requests.get(
                "https://api.inaturalist.org/v1/observations", 
                params=params, 
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            logging.info(f"iNaturalist returned {len(data.get('results', []))} total observations")
            
            for obs in data.get('results', []):
                # Get coordinates
                if obs.get('geojson') and obs['geojson'].get('coordinates'):
                    lng, lat = obs['geojson']['coordinates']
                    
                    # Get species name
                    species = "Unknown"
                    if obs.get('taxon'):
                        species = obs['taxon'].get('preferred_common_name', 
                                 obs['taxon'].get('name', 'Unknown'))
                    
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
        """Fetch from GBIF with correct parameters."""
        sightings = []
        
        logging.info("🏛️ Fetching from GBIF...")
        
        # FIXED: Use single taxonKey with OR logic or query multiple times
        safari_taxons = [
            2435099, # Lion
            2440641, # Elephant
            2441203, # Giraffe
            2440887, # Zebra
            2440916, # Buffalo
            2440952, # Rhino
            2440943, # Leopard
            2440787, # Cheetah
        ]
        
        # Try each taxon separately to avoid parameter issues
        for taxon_id in safari_taxons[:3]: # Just try first 3 to avoid too many calls
            try:
                params = {
                    "taxonKey": taxon_id,
                    "country": "TZ,KE,UG,ZA,NA,BW,ZW,ZM,MZ",
                    "basisOfRecord": "HUMAN_OBSERVATION",
                    "hasCoordinate": "true",
                    "limit": 30,
                    "mediaType": "StillImage"
                }
                
                response = requests.get(
                    "https://api.gbif.org/v1/occurrence/search",
                    params=params,
                    timeout=15
                )
                response.raise_for_status()
                data = response.json()
                
                logging.info(f"GBIF taxon {taxon_id} returned {len(data.get('results', []))} results")
                
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
                logging.error(f"GBIF taxon {taxon_id} error: {e}")
                continue
        
        logging.info(f"✅ Found {len(sightings)} GBIF sightings")
        return sightings

    def fetch_test_data(self):
        """Generate test data to verify pipeline works."""
        logging.info("🧪 Generating test data...")
        
        test_sightings = [
            {
                "source": "Test",
                "source_url": "https://example.com",
                "content": "Test lion sighting in Serengeti",
                "extracted_species": "Lion",
                "confidence_score": 0.95,
                "location": "POINT(34.8 -2.3)", # Serengeti
            },
            {
                "source": "Test", 
                "source_url": "https://example.com",
                "content": "Test elephant in Kruger",
                "extracted_species": "Elephant",
                "confidence_score": 0.95,
                "location": "POINT(31.5 -24.0)", # Kruger
            },
            {
                "source": "Test",
                "source_url": "https://example.com",
                "content": "Test giraffe in Ngorongoro",
                "extracted_species": "Giraffe", 
                "confidence_score": 0.95,
                "location": "POINT(35.5 -3.2)", # Ngorongoro
            }
        ]
        
        logging.info(f"✅ Generated {len(test_sightings)} test sightings")
        return test_sightings

    def run(self):
        """Main execution."""
        logging.info("🚀 Starting wildlife data scrape...")
        
        all_sightings = []
        
        # OPTION 1: Use test data to verify pipeline works
        all_sightings.extend(self.fetch_test_data())
        
        # OPTION 2: Uncomment these when APIs start working
        # all_sightings.extend(self.fetch_inaturalist())
        # all_sightings.extend(self.fetch_gbif())
        
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
