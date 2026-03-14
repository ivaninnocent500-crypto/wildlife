import os
import asyncio
from supabase import create_client, Client

async def process_habitats():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("❌ ERROR: Environmental script cannot find SUPABASE_URL or SUPABASE_KEY.")
        return

    print("🌍 Calculating Environmental Features (NDVI/Water)...")
   
    supabase: Client = create_client(url, key)
   
    # Habitat processing logic goes here
    print("✅ Habitat processing complete.")

if __name__ == "__main__":
    asyncio.run(process_habitats())

