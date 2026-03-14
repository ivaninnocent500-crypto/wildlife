import os
import asyncio
from supabase import create_client, Client

async def process_habitats():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)

    print("🌍 Fetching raw reports for processing...")

    # 1. Get unprocessed reports
    reports = supabase.table("crowdsourced_reports").select("*").execute()

    for report in reports.data:
        # Extract coordinates from the POINT string
        # "POINT(34.8233 -2.3333)" -> [34.8233, -2.3333]
        raw_loc = report.get('location')
        if not raw_loc: continue
        
        # Simple cleanup to get lat/lng for processing
        coords = raw_loc.replace("POINT(", "").replace(")", "").split()
        lng, lat = float(coords[0]), float(coords[1])

        # 2. Simulated Habitat Logic (Replace with actual API calls later)
        # Here we 'calculate' the greenness (NDVI) and distance to water
        ndvi = 0.45 
        water_dist = 150.0 

        # 3. Move to 'sightings' table (The table your Android app reads)
        sighting_data = {
            "species_name": report['extracted_species'],
            "location": report['location'],
            "ndvi_value": ndvi,
            "distance_to_water": water_dist,
            "timestamp": report['created_at']
        }

        try:
            supabase.table("sightings").insert(sighting_data).execute()
            # 4. Delete from raw reports so we don't process it twice
            supabase.table("crowdsourced_reports").delete().eq("id", report['id']).execute()
            print(f"✅ Processed and Moved: {report['extracted_species']}")
        except Exception as e:
            print(f"⚠️ Error moving data: {e}")

if __name__ == "__main__":
    asyncio.run(process_habitats())
