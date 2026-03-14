import os
import asyncio
from supabase import create_client

# GitHub Actions will inject these from your "Secrets"
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

async def run_scraper():
    print("🚀 Starting Wildlife Scraper...")
    # This matches your social media scraper structure
    # Scraping logic goes here
    print("✅ Data synced to Supabase.")

if __name__ == "__main__":
    asyncio.run(run_scraper())
