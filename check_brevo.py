import asyncio
import httpx
import os
from dotenv import load_dotenv

async def check_brevo():
    load_dotenv()
    api_key = os.getenv("BREVO_API_KEY")
    base_url = os.getenv("BREVO_BASE_URL", "https://api.brevo.com/v3")
    
    if not api_key:
        print("BREVO_API_KEY not found in .env")
        return

    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    async with httpx.AsyncClient(base_url=base_url, headers=headers) as client:
        print(f"Making request to {base_url}/account...")
        try:
            response = await client.get("/account")
            print(f"Status Code: {response.status_code}")
            
            print("\nRelevant Headers:")
            for k, v in response.headers.items():
                if any(x in k.lower() for x in ["rate", "limit", "quota", "request"]):
                    print(f"{k}: {v}")
                
            if response.status_code == 200:
                print("\nRequest Succeeded.")
                data = response.json()
                print(f"Plan: {data.get('plan')}")
            else:
                print(f"\nBody: {response.text}")
                
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_brevo())
