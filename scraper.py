import os
import asyncio
from supabase import create_client

async def run_scraper():
    # 1. Pull the secrets from GitHub Environment
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    # 2. Safety Check: If these are empty, stop and print a clear message
    if not url or not key:
        print("❌ CRITICAL ERROR: SUPABASE_URL or SUPABASE_KEY is missing!")
        print("Check GitHub Repo > Settings > Secrets and variables > Actions")
        return # Exit the function early

    print("🚀 Starting Wildlife Scraper...")
    
    # 3. Initialize the client safely inside the function
    supabase = create_client(url, key)
    
    # YOUR SCRAPING LOGIC GOES HERE
    # Example: print("Found a Lion sighting at Serengeti!")

    print("✅ Data synced to Supabase.")

if __name__ == "__main__":
    asyncio.run(run_scraper())

