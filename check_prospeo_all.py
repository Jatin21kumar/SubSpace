import asyncio
import httpx
import os
from dotenv import load_dotenv

async def check_prospeo():
    load_dotenv()
    api_key = os.getenv("PROSPEO_API_KEY")
    base_url = os.getenv("PROSPEO_BASE_URL", "https://api.prospeo.io")
    
    if not api_key:
        print("PROSPEO_API_KEY not found in .env")
        return

    headers = {
        "X-KEY": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    body = {
        "filters": {
            "company": {"websites": {"include": ["google.com"]}}
        },
        "page": 1
    }
    
    async with httpx.AsyncClient(base_url=base_url, headers=headers) as client:
        print(f"Making request to {base_url}/search-person...")
        try:
            response = await client.post("/search-person", json=body)
            print(f"Status Code: {response.status_code}")
            
            print("\nAll Headers:")
            for k, v in response.headers.items():
                print(f"{k}: {v}")
                
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_prospeo())
