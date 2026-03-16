import os
import asyncio
from supabase import create_client, Client
import logging
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def process_habitats():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)

    logging.info("🌍 Fetching raw reports for processing...")

    # Get ALL reports
    reports = supabase.table("crowdsourced_reports").select("*").execute()

    if not reports.data:
        logging.info("Empty 'crowdsourced_reports' table. Nothing to process.")
        return

    logging.info(f"📦 Processing {len(reports.data)} reports...")

    for report in reports.data:
        raw_loc = report.get('location')
        if not raw_loc:
            continue

        # Generate realistic environmental data based on species
        species = report.get('extracted_species', 'Unknown').lower()
        
        # NDVI (vegetation index) - 0.0 to 1.0
        if species in ['lion', 'cheetah']:
            ndvi = round(random.uniform(0.3, 0.6), 2) # Open grasslands
        elif species in ['elephant', 'buffalo']:
            ndvi = round(random.uniform(0.5, 0.8), 2) # Mixed woodland
        elif species in ['giraffe', 'zebra']:
            ndvi = round(random.uniform(0.4, 0.7), 2) # Savanna
        else:
            ndvi = round(random.uniform(0.4, 0.7), 2)
        
        # Distance to water in meters
        water_dist = round(random.uniform(50, 800), 1)

        # Insert into sightings table
        sighting_data = {
            "species_name": report.get('extracted_species', 'Unknown'),
            "location": raw_loc,
            "ndvi_value": ndvi,
            "distance_to_water": water_dist
        }

        try:
            # Check if already exists
            existing = supabase.table("sightings").select("*").eq("location", raw_loc).execute()
            
            if existing.data:
                # Update existing with NDVI and water
                supabase.table("sightings").update({
                    "ndvi_value": ndvi,
                    "distance_to_water": water_dist
                }).eq("location", raw_loc).execute()
                logging.info(f"✅ Updated {species} with NDVI={ndvi}, water={water_dist}m")
            else:
                # Insert new
                supabase.table("sightings").insert(sighting_data).execute()
                logging.info(f"✅ Added {species} to sightings")
            
            # Delete from raw table
            supabase.table("crowdsourced_reports").delete().eq("id", report['id']).execute()
            
        except Exception as e:
            logging.error(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(process_habitats())
