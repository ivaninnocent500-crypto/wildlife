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

    # 2. THE SCRAPER LOGIC
    # For now, we are simulating found data. 
    # You can replace 'found_data' with your specific scraping results.
    found_data = [
        {
            "source": "Social Media Scraper",
            "source_url": "https://example.com/post/123",
            "content": "Large male Lion spotted near Seronera water hole!",
            "extracted_species": "Lion",
            "confidence_score": 0.95
        },
        {
            "source": "Park Report",
            "source_url": "https://example.com/report/456",
            "content": "Group of 3 Cheetahs moving North from Naabi Gate.",
            "extracted_species": "Cheetah",
            "confidence_score": 0.88
        }
    ]

    # 3. Insert into Supabase
    for sighting in found_data:
        try:
            # This matches your SQL table: crowdsourced_reports
            response = supabase.table("crowdsourced_reports").upsert(sighting).execute()
            print(f"✅ Synced: {sighting['extracted_species']} from {sighting['source']}")
        except Exception as e:
            print(f"⚠️ Failed to sync sighting: {e}")

    print("🏁 Scraper cycle complete.")

if __name__ == "__main__":
    asyncio.run(run_scraper())
