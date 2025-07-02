#!/usr/bin/env python3
"""
Script to populate the F1 database with current season data.
Run this script to fetch and store all F1 data from the APIs into your Supabase database.
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any

# Configuration
API_BASE_URL = "http://localhost:8000"

async def call_endpoint(session: aiohttp.ClientSession, endpoint: str, description: str) -> Dict[str, Any]:
    """Call a single API endpoint and return the response"""
    try:
        print(f"📡 Fetching {description}...")
        async with session.post(f"{API_BASE_URL}{endpoint}") as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ {description}: {data.get('message', 'Success')}")
                return data
            else:
                error_text = await response.text()
                print(f"❌ {description}: HTTP {response.status} - {error_text}")
                return {"error": error_text, "status": response.status}
    except Exception as e:
        print(f"❌ {description}: {str(e)}")
        return {"error": str(e)}

async def populate_database():
    """Populate all database tables with F1 data"""
    print("🏎️  F1 Database Population Script")
    print("=" * 50)
    
    # Endpoints to call in order
    endpoints = [
        ("/api/current-drivers/f1api", "Drivers Data"),
        ("/api/current-teams/f1api", "Teams Data"),
        ("/api/current-drivers-standings/f1api", "Driver Championship Standings"),
        ("/api/current-teams-standings/f1api", "Constructor Championship Standings"),
    ]
    
    async with aiohttp.ClientSession() as session:
        results = []
        
        for endpoint, description in endpoints:
            result = await call_endpoint(session, endpoint, description)
            results.append({
                "endpoint": endpoint,
                "description": description,
                "result": result
            })
            # Small delay between requests
            await asyncio.sleep(1)
        
        print("\n" + "=" * 50)
        print("📊 SUMMARY")
        print("=" * 50)
        
        success_count = 0
        for item in results:
            if "error" not in item["result"]:
                success_count += 1
                print(f"✅ {item['description']}")
            else:
                print(f"❌ {item['description']}: {item['result']['error']}")
        
        print(f"\n🎯 {success_count}/{len(results)} endpoints completed successfully")
        
        if success_count == len(results):
            print("\n🎉 Database population completed successfully!")
            print("Your frontend should now display live data from the database.")
        else:
            print("\n⚠️  Some endpoints failed. Check the errors above.")
            print("Make sure your FastAPI server is running on http://localhost:8000")

async def verify_data():
    """Verify that data was loaded correctly"""
    print("\n🔍 Verifying database content...")
    
    verify_endpoints = [
        ("/api/drivers", "Drivers"),
        ("/api/teams", "Teams"),
        ("/api/drivers-standings", "Driver Standings"),
        ("/api/teams-standings", "Constructor Standings"),
    ]
    
    async with aiohttp.ClientSession() as session:
        for endpoint, description in verify_endpoints:
            try:
                async with session.get(f"{API_BASE_URL}{endpoint}") as response:
                    if response.status == 200:
                        data = await response.json()
                        if "drivers" in data:
                            count = len(data["drivers"])
                        elif "teams" in data:
                            count = len(data["teams"])
                        elif "standings" in data:
                            count = len(data["standings"])
                        else:
                            count = "Unknown"
                        print(f"✅ {description}: {count} records")
                    else:
                        print(f"❌ {description}: HTTP {response.status}")
            except Exception as e:
                print(f"❌ {description}: {str(e)}")

if __name__ == "__main__":
    print("Starting F1 database population...")
    print("Make sure your FastAPI server is running on http://localhost:8000")
    print()
    
    try:
        asyncio.run(populate_database())
        asyncio.run(verify_data())
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}") 