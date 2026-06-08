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
    
    # Simple search-person request that might fail or succeed but should return headers
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
            
            prospeo_headers = {k: v for k, v in response.headers.items() if k.lower().startswith("x-")}
            print("\nProspeo Headers:")
            for k, v in prospeo_headers.items():
                print(f"{k}: {v}")
                
            if response.status_code == 429:
                print("\nRate Limit Exceeded!")
                try:
                    error_data = response.json()
                    print(f"Error: {error_data}")
                except:
                    print(f"Body: {response.text}")
            elif response.status_code == 200:
                print("\nRequest Succeeded.")
            else:
                print(f"\nUnexpected status code: {response.status_code}")
                print(f"Body: {response.text}")
                
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_prospeo())
