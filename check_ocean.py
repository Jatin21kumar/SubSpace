import asyncio
import httpx
import os
from dotenv import load_dotenv

async def check_ocean():
    load_dotenv()
    api_key = os.getenv("OCEAN_API_KEY")
    base_url = os.getenv("OCEAN_BASE_URL", "https://api.ocean.io/v3")
    
    if not api_key:
        print("OCEAN_API_KEY not found in .env")
        return

    headers = {
        "X-Api-Token": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    payload = {
        "companiesFilters": {
            "lookalikeDomains": ["google.com"]
        },
        "size": 1,
        "fields": ["name", "domain"],
    }
    
    async with httpx.AsyncClient(base_url=base_url, headers=headers) as client:
        print(f"Making request to {base_url}/search/companies...")
        try:
            response = await client.post("/search/companies", json=payload)
            print(f"Status Code: {response.status_code}")
            
            print("\nRelevant Headers:")
            for k, v in response.headers.items():
                if any(x in k.lower() for x in ["rate", "limit", "quota", "request"]):
                    print(f"{k}: {v}")
                
            if response.status_code == 200:
                print("\nRequest Succeeded.")
            else:
                print(f"\nBody: {response.text}")
                
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_ocean())
