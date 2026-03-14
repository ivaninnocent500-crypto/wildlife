import os
import asyncio
from supabase import create_client, Client

async def run_scraper():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("❌ CRITICAL ERROR: Secrets missing.")
        return 

    # 1. Initialize Supabase
    supabase: Client = create_client(url, key)
    print("🚀 Connection Established. Searching for sightings...")

    # 1. NEW DATA with Location Coordinates
    # Format: "POINT(longitude latitude)"
    found_data = [
        {
            "source": "Social Media",
            "source_url": "https://example.com/lion1",
            "content": "Lion near Seronera",
            "extracted_species": "Lion",
            "confidence_score": 0.95,
            "location": "POINT(34.8233 -2.3333)" # Serengeti Coordinates
        },
        {
            "source": "Guide Report",
            "source_url": "https://example.com/leopard1",
            "content": "Leopard in Ngorongoro",
            "extracted_species": "Leopard",
            "confidence_score": 0.88,
            "location": "POINT(35.5873 -3.2458)" # Ngorongoro Coordinates
        }
    ]

    for sighting in found_data:
        try:
            # Upsert will now fill the 'location' column
            supabase.table("crowdsourced_reports").upsert(sighting).execute()
            print(f"✅ Synced {sighting['extracted_species']} with Location!")
        except Exception as e:
            print(f"⚠️ Sync failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_scraper())
