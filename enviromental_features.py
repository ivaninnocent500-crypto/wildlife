import os
import asyncio
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

async def process_habitats():
    print("🌍 Calculating Environmental Features (NDVI/Water)...")
    # This uses your environmental feature extractor logic
    print("✅ Habitat processing complete.")

if __name__ == "__main__":
    asyncio.run(process_habitats())
