import asyncio
import os
import json
from outreach_tool.apis.oceanio import OceanIOClient
from outreach_tool.core.config import get_config

async def main():
    config = get_config()
    
    async with OceanIOClient() as client:
        print("--- Real Request Validation ---")
        seed_domain = "stripe.com"
        
        # We'll use a small limit for validation
        companies = await client.find_similar_companies(seed_domain, limit=1)
        
        if companies:
            company = companies[0]
            print(f"Response status: SUCCESS")
            print(f"First company found: '{company.name}' ('{company.domain}')")
            print(f"Raw data: {json.dumps(company.raw_data, indent=2)}")
        else:
            print("No companies found or request failed.")

if __name__ == "__main__":
    asyncio.run(main())
