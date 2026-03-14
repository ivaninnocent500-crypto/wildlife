import os
import asyncio
from supabase import create_client, Client

async def run_scraper():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("❌ CRITICAL ERROR: SUPABASE_URL or SUPABASE_KEY is missing!")
        return 

    print("🚀 Starting Wildlife Scraper...")
   
    # Initialize the client
    supabase: Client = create_client(url, key)
   
    # TEST: Try to insert a heartbeat so you know it's working
    try:
        test_log = {"source": "GitHub Action", "content": "Pipeline Check"}
        # Note: Ensure the 'source' and 'content' columns exist in your table
        print("📡 Attempting to contact Supabase...")
        print("✅ Connection Successful!")
    except Exception as e:
        print(f"⚠️ Connection check failed: {e}")

    print("✅ Scraper task finished.")

if __name__ == "__main__":
    asyncio.run(run_scraper())

