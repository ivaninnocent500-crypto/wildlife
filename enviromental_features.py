import os
import asyncio
from supabase import create_client, Client

async def process_habitats():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)

    print("🌍 Fetching raw reports for processing...")

    # 1. Use RPC or a custom select to get the location as text
    # We select 'location' but we will handle the hex conversion in Python
    reports = supabase.table("crowdsourced_reports").select("*").execute()

    if not reports.data:
        print("Empty 'crowdsourced_reports' table. Nothing to process.")
        return

    for report in reports.data:
        # THE FIX: Supabase sometimes returns hex for Geography types. 
        # If we can't parse it simply, we skip or use a parser.
        raw_loc = report.get('location')
        if not raw_loc:
            continue

        print(f"📦 Processing report ID: {report['id']}")

        # Step 2: Extract Coordinates
        # If it's a HEX string from PostGIS, we need to handle it.
        # For now, let's simplify by assuming we want to move the data.
        
        # Simulated Habitat Logic (NDVI/Water)
        ndvi = 0.52 
        water_dist = 200.0 

        # 3. Move to 'sightings' table
        # We pass the location hex directly back; Supabase knows how to handle it on INSERT
        sighting_data = {
            "species_name": report.get('extracted_species', 'Unknown'),
            "location": raw_loc, # Keep the hex, the DB will re-parse it
            "ndvi_value": ndvi,
            "distance_to_water": water_dist
        }

        try:
            # Insert into the final table that the Android App uses
            supabase.table("sightings").insert(sighting_data).execute()
            
            # Delete from raw table so we don't process it again
            supabase.table("crowdsourced_reports").delete().eq("id", report['id']).execute()
            print(f"✅ Successfully moved {sighting_data['species_name']} to sightings table.")
        except Exception as e:
            print(f"⚠️ Error during transfer: {e}")

if __name__ == "__main__":
    asyncio.run(process_habitats())
