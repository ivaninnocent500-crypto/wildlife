import os
import asyncio
from supabase import create_client

async def process_habitats():
    # 1. Pull the secrets
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    # 2. Safety Check
    if not url or not key:
        print("❌ ERROR: Environmental script cannot find SUPABASE_URL or SUPABASE_KEY.")
        print("Ensure they are added to GitHub Secrets and mapped in the YAML file.")
        return

    print("🌍 Calculating Environmental Features (NDVI/Water)...")
    
    # 3. Initialize client
    supabase = create_client(url, key)
    
    # Your Step 3 processing logic here
    print("✅ Habitat processing complete.")

if __name__ == "__main__":
    asyncio.run(process_habitats())
