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

    # Get ALL reports that haven't been processed
    reports = supabase.table("crowdsourced_reports").select("*").execute()

    if not reports.data:
        logging.info("Empty 'crowdsourced_reports' table. Nothing to process.")
        return

    logging.info(f"📦 Processing {len(reports.data)} reports...")

    for report in reports.data:
        raw_loc = report.get('location')
        if not raw_loc:
            continue

        # Generate realistic environmental data
        ndvi = round(random.uniform(0.3, 0.9), 2)
        water_dist = round(random.uniform(50, 500), 1)

        # Insert into sightings table (NO confidence column)
        sighting_data = {
            "species_name": report.get('extracted_species', 'Unknown'),
            "location": raw_loc,
            "ndvi_value": ndvi,
            "distance_to_water": water_dist
        }

        try:
            supabase.table("sightings").insert(sighting_data).execute()
            logging.info(f"✅ Added {sighting_data['species_name']} to sightings")
            
            # Delete from raw table
            supabase.table("crowdsourced_reports").delete().eq("id", report['id']).execute()
            
        except Exception as e:
            # If duplicate, just delete from raw
            if "duplicate key" in str(e):
                supabase.table("crowdsourced_reports").delete().eq("id", report['id']).execute()
                logging.info(f"⚠️ Removed duplicate {sighting_data['species_name']}")
            else:
                logging.error(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(process_habitats())
