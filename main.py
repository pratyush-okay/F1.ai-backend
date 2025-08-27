# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
from typing import List, Dict, Any, Optional
import asyncio
import re
import os
import logging
from supabase import create_client, Client
from postgrest import APIResponse
from dotenv import load_dotenv
from datetime import datetime, date
from pathlib import Path
import json

# Set up logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables - update for production
load_dotenv(dotenv_path=Path(".env.dev"))

# For production, also try to load from environment directly
SUPABASE_DEV_URL = os.getenv("SUPABASE_DEV_URL") or os.getenv("SUPABASE_URL")
SUPABASE_DEV_KEY = os.getenv("SUPABASE_DEV_KEY") or os.getenv("SUPABASE_KEY")

# Add validation for required environment variables
if not SUPABASE_DEV_URL or not SUPABASE_DEV_KEY:
    logger.error("Missing required environment variables: SUPABASE_DEV_URL and SUPABASE_DEV_KEY")
    logger.error(f"SUPABASE_DEV_URL: {SUPABASE_DEV_URL}")
    logger.error(f"SUPABASE_DEV_KEY: {'***' if SUPABASE_DEV_KEY else 'None'}")
    # Don't exit, but log the error so we can see it in Railway logs

try:
    supabase: Client = create_client(SUPABASE_DEV_URL, SUPABASE_DEV_KEY)
    logger.info("Supabase client created successfully")
except Exception as e:
    logger.error(f"Failed to create Supabase client: {e}")
    # Continue anyway so the app starts and we can debug


app = FastAPI(title="Formula1.ai API", description="F1 data API using OpenF1")

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

# CORS configuration
origins = [
    frontend_url,
    "http://localhost:3000",  # for local development
    "http://localhost:3001",  # additional local ports if needed
    "https://f1ai-frontend-production.up.railway.app/",  # Railway default domain
    "https://www.formula1.ai",  # Your custom domain
    "https://formula1.ai",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add startup event to log when the app starts
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 FastAPI application starting up!")
    logger.info(f"Supabase URL configured: {'Yes' if SUPABASE_DEV_URL else 'No'}")
    logger.info(f"Supabase Key configured: {'Yes' if SUPABASE_DEV_KEY else 'No'}")
    logger.info(f"PORT environment variable: {os.getenv('PORT')}")


# Driver numbers mapping based on 2025 season data
DRIVER_NUMBERS = [1, 4, 5, 6, 10, 12, 14, 16, 18, 22, 23, 27, 30, 31, 43, 44, 55, 63, 81, 87]

def normalize_name(name: str) -> str:
    """Normalize driver name for matching"""
    if not name:
        return ""
    # Remove special characters and convert to lowercase
    normalized = re.sub(r'[^a-zA-Z\s]', '', name.lower())
    # Replace spaces with underscores
    return normalized.replace(' ', '_')

def find_driver_standing(driver_name: str, name_acronym: str, standings_data: Dict) -> Dict:
    """Find matching driver standing using multiple strategies"""
    if not standings_data:
        return {}
    
    logger.info(f"Looking for driver: {driver_name} ({name_acronym})")
    
    # Strategy 1: Direct match with driverId
    if driver_name in standings_data:
        logger.info(f"Found direct match: {driver_name}")
        return standings_data[driver_name]
    
    # Strategy 2: Match with normalized full name
    normalized_name = normalize_name(driver_name)
    if normalized_name in standings_data:
        logger.info(f"Found normalized match: {normalized_name}")
        return standings_data[normalized_name]
    
    # Strategy 3: Match with acronym
    if name_acronym and name_acronym.lower() in standings_data:
        logger.info(f"Found acronym match: {name_acronym.lower()}")
        return standings_data[name_acronym.lower()]
    
    # Strategy 4: Partial name matching
    for key, value in standings_data.items():
        # Check if any part of the driver name matches
        driver_parts = driver_name.lower().split()
        key_parts = key.replace('_', ' ').split()
        
        # Check if surnames match
        if driver_parts and key_parts and driver_parts[-1] == key_parts[-1]:
            logger.info(f"Found surname match: {driver_parts[-1]} -> {key}")
            return value
        
        # Check if first names match
        if driver_parts and key_parts and driver_parts[0] == key_parts[0]:
            logger.info(f"Found first name match: {driver_parts[0]} -> {key}")
            return value
    
    logger.warning(f"No match found for driver: {driver_name}")
    return {}

@app.get("/")
def read_root():
    return {"message": "Formula1.ai API - Ready to serve F1 data!"}

# Add a simple health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# Add this simple endpoint that doesn't use database
@app.get("/test")
def test_endpoint():
    return {
        "status": "ok", 
        "message": "Test endpoint working",
        "timestamp": datetime.utcnow().isoformat(),
        "supabase_url_set": bool(SUPABASE_DEV_URL),
        "supabase_key_set": bool(SUPABASE_DEV_KEY)
    }
@app.get("/api/driver-standings")
async def get_driver_standings():
    """Fetch current driver championship standings from Supabase database (frontend compatibility)"""
    try:
        # Query to get driver standings with driver and team details
        standings_result = supabase.table("current_drivers_standings").select("*").order("position").execute()
        drivers_result = supabase.table("current_drivers").select("*").execute()
        teams_result = supabase.table("current_teams").select("*").execute()
        
        # Create lookup dictionaries
        drivers_dict = {d['driver_id']: d for d in drivers_result.data}
        teams_dict = {t['team_id']: t for t in teams_result.data}
        
        # Format data to match frontend expectations
        drivers_championship = []
        for standing in standings_result.data:
            driver_info = drivers_dict.get(standing['driver_id'], {})
            team_info = teams_dict.get(standing['team_id'], {})
            
            drivers_championship.append({
                "classificationId": standing.get('classification_id'),
                "driverId": standing.get('driver_id'),
                "teamId": standing.get('team_id'),
                "points": standing.get('points', 0),
                "position": standing.get('position'),
                "wins": standing.get('wins'),
                "driver": {
                    "name": driver_info.get('name', ''),
                    "surname": driver_info.get('surname', ''),
                    "nationality": driver_info.get('nationality', ''),
                    "birthday": driver_info.get('birthday', ''),
                    "number": driver_info.get('number'),
                    "shortName": driver_info.get('short_name', ''),
                    "url": driver_info.get('url', '')
                },
                "team": {
                    "teamId": team_info.get('team_id', ''),
                    "teamName": team_info.get('team_name', ''),
                    "country": team_info.get('team_nationality', ''),
                    "firstAppareance": team_info.get('first_appearance'),
                    "constructorsChampionships": team_info.get('constructors_championships'),
                    "driversChampionships": team_info.get('drivers_championships'),
                    "url": team_info.get('url', '')
                }
            })
        
        logger.info(f"Retrieved {len(drivers_championship)} driver standings from database")
        
        return {
            "api": "F1 API",
            "url": "https://f1api.dev/api/current/drivers-championship",
            "limit": 30,
            "offset": 0,
            "total": len(drivers_championship),
            "season": standing.get('season', 2025) if standings_result.data else 2025,
            "championshipId": standing.get('championship_id', 'f1_2025') if standings_result.data else 'f1_2025',
            "drivers_championship": drivers_championship
        }
            
    except Exception as e:
        logger.error(f"Error fetching driver standings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/drivers")
async def get_drivers():
    """Fetch all current F1 drivers from Supabase database with championship standings"""
    
    # Team color mapping function - define outside try/except for universal access
    def get_team_color(team_name: str) -> str:
        team_colors = {
            'Red Bull Racing': '0600EF',
            'McLaren Formula 1 Team': 'FF8700', 
            'McLaren': 'FF8700',
            'Scuderia Ferrari': 'DC0000',
            'Ferrari': 'DC0000',
            'Mercedes Formula 1 Team': '00D2BE',
            'Mercedes': '00D2BE',
            'Aston Martin F1 Team': '006F62',
            'Aston Martin': '006F62',
            'Alpine F1 Team': '0090FF',
            'Alpine': '0090FF',
            'Williams Racing': '005AFF',
            'Williams': '005AFF',
            'RB F1 Team': '6692FF',
            'RB': '6692FF',
            'Haas F1 Team': 'FFFFFF',
            'Haas': 'FFFFFF',
            'Sauber F1 Team': '52E252',
            'Sauber': '52E252'
        }
        return team_colors.get(team_name, 'FF1E1E')
    
    try:
        # Fetch data using individual table queries (no RPC needed)
        drivers_result = supabase.table("current_drivers").select("*").execute()
        standings_result = supabase.table("current_drivers_standings").select("*").execute()
        teams_result = supabase.table("current_teams").select("*").execute()
        
        drivers_data = drivers_result.data
        standings_data = {s['driver_id']: s for s in standings_result.data}
        teams_data = {t['team_id']: t for t in teams_result.data}
        
        formatted_drivers = []
        for driver in drivers_data:
            standing = standings_data.get(driver['driver_id'], {})
            team = teams_data.get(driver['team_id'], {})
            full_name = f"{driver.get('name', '')} {driver.get('surname', '')}".strip()
            team_name = team.get('team_name', '')
            
            formatted_drivers.append({
                "id": driver.get('number'),
                "driver_number": driver.get('number'),
                "first_name": driver.get('name', ''),
                "last_name": driver.get('surname', ''),
                "full_name": full_name,
                "broadcast_name": full_name,
                "name_acronym": driver.get('short_name', ''),
                "country_code": driver.get('nationality', ''),
                "team_name": team_name,
                "team_colour": get_team_color(team_name),
                "headshot_url": f"/drivers/{full_name}.avif",
                "nationality": driver.get('nationality', ''),
                "team": team_name,
                "number": driver.get('number'),
                "image": f"/drivers/{full_name}.avif",
                "championship_position": standing.get('position'),
                "championship_points": standing.get('points', 0),
                "wins": standing.get('wins', 0)
            })
        
        # Sort by championship position
        formatted_drivers.sort(key=lambda x: (x.get('championship_position') or 999, x.get('number') or 999))
        
        logger.info(f"Retrieved {len(formatted_drivers)} drivers from database")
        
        return {
            "drivers": formatted_drivers,
            "total": len(formatted_drivers)
        }
            
    except Exception as e:
        logger.error(f"Error fetching drivers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching drivers: {str(e)}")

@app.get("/api/drivers/{driver_number}")
async def get_driver(driver_number: int):
    """Fetch specific driver by number from Supabase database"""
    try:
        # Fetch driver with championship standings and team info
        driver_result = supabase.table("current_drivers").select("*").eq("number", driver_number).execute()
        
        if not driver_result.data:
            raise HTTPException(status_code=404, detail=f"Driver with number {driver_number} not found")
        
        driver = driver_result.data[0]
        
        # Get standings and team info
        standing_result = supabase.table("current_drivers_standings").select("*").eq("driver_id", driver['driver_id']).execute()
        team_result = supabase.table("current_teams").select("*").eq("team_id", driver['team_id']).execute()
        
        standing = standing_result.data[0] if standing_result.data else {}
        team = team_result.data[0] if team_result.data else {}
        
        # Team color mapping (same as in get_drivers)
        def get_team_color(team_name: str) -> str:
            team_colors = {
                'Red Bull Racing': '0600EF',
                'McLaren Formula 1 Team': 'FF8700', 
                'McLaren': 'FF8700',
                'Scuderia Ferrari': 'DC0000',
                'Ferrari': 'DC0000',
                'Mercedes Formula 1 Team': '00D2BE',
                'Mercedes': '00D2BE',
                'Aston Martin F1 Team': '006F62',
                'Aston Martin': '006F62',
                'Alpine F1 Team': '0090FF',
                'Alpine': '0090FF',
                'Williams Racing': '005AFF',
                'Williams': '005AFF',
                'RB F1 Team': '6692FF',
                'RB': '6692FF',
                'Haas F1 Team': 'FFFFFF',
                'Haas': 'FFFFFF',
                'Sauber F1 Team': '52E252',
                'Sauber': '52E252'
            }
            return team_colors.get(team_name, 'FF1E1E')
        
        full_name = f"{driver.get('name', '')} {driver.get('surname', '')}".strip()
        team_name = team.get('team_name', '')
        
        return {
            "id": driver.get('number'),
            "driver_number": driver.get('number'),
            "first_name": driver.get('name', ''),
            "last_name": driver.get('surname', ''),
            "full_name": full_name,
            "broadcast_name": full_name,
            "name_acronym": driver.get('short_name', ''),
            "country_code": driver.get('nationality', ''),
            "team_name": team_name,
            "team_colour": get_team_color(team_name),
            "headshot_url": f"/drivers/{full_name}.avif",
            "nationality": driver.get('nationality', ''),
            "team": team_name,
            "number": driver.get('number'),
            "image": f"/drivers/{full_name}.avif",
            "championship_position": standing.get('position'),
            "championship_points": standing.get('points', 0),
            "wins": standing.get('wins', 0)
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching driver {driver_number}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")



def upsert_f1api_drivers(drivers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for d in drivers:
        try:
            rows.append(
                {
                    "driver_id": d.get("driverId") or "",
                    "name": d.get("name") or "",
                    "surname": d.get("surname") or "",
                    "nationality": d.get("nationality") or "",
                    "birthday": d.get("birthday") or "",
                    "number": int(d.get("number") or 0),
                    "short_name": d.get("shortName") or "",
                    "url": d.get("url") or "",
                    "team_id": d.get("teamId") or "",
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
        except Exception as row_err:
            logging.warning("Skipping row (parse error): %s – %s", d, row_err)

    # The SDK will raise PostgrestAPIError on 409 / 400 / 500, so no need
    # to probe status_code. If we get past .execute() it was a success.
    result: APIResponse = (
        supabase.table("current_drivers")
        .upsert(
            rows,
            on_conflict="driver_id",
            ignore_duplicates=True,
            returning="representation",  # to get back the rows we wrote
        )
        .execute()
    )

    # result.data is always a list (may be empty) on success
    return result.data

def upsert_f1api_teams(teams: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for t in teams:
        try:
            rows.append(
                {
                    "team_id": t.get("teamId") or "",
                    "team_name": t.get("teamName") or "",
                    "team_nationality": t.get("teamNationality") or "",
                    "first_appearance": int(t.get("firstAppeareance") or 0),  # Note: API has typo "Appeareance"
                    "constructors_championships": int(t.get("constructorsChampionships")) if t.get("constructorsChampionships") is not None else None,
                    "drivers_championships": int(t.get("driversChampionships")) if t.get("driversChampionships") is not None else None,
                    "url": t.get("url") or "",
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
        except Exception as row_err:
            logging.warning("Skipping row (parse error): %s – %s", t, row_err)

    # The SDK will raise PostgrestAPIError on 409 / 400 / 500, so no need
    # to probe status_code. If we get past .execute() it was a success.
    result: APIResponse = (
        supabase.table("current_teams")
        .upsert(
            rows,
            on_conflict="team_id",
            ignore_duplicates=True,
            returning="representation",  # to get back the rows we wrote
        )
        .execute()
    )

    # result.data is always a list (may be empty) on success
    return result.data

def upsert_f1api_driver_standings(standings: List[Dict[str, Any]], season: int, championship_id: str) -> List[Dict[str, Any]]:
    rows = []
    for s in standings:
        try:
            rows.append(
                {
                    "classification_id": int(s.get("classificationId") or 0),
                    "driver_id": s.get("driverId") or "",
                    "team_id": s.get("teamId") or "",
                    "season": season,
                    "championship_id": championship_id,
                    "points": int(s.get("points") or 0),
                    "position": int(s.get("position") or 0),
                    "wins": int(s.get("wins")) if s.get("wins") is not None else None,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
        except Exception as row_err:
            logging.warning("Skipping row (parse error): %s – %s", s, row_err)

    # The SDK will raise PostgrestAPIError on 409 / 400 / 500, so no need
    # to probe status_code. If we get past .execute() it was a success.
    result: APIResponse = (
        supabase.table("current_drivers_standings")
        .upsert(
            rows,
            on_conflict="classification_id",
            ignore_duplicates=False,
            returning="representation",  # to get back the rows we wrote
        )
        .execute()
    )

    # result.data is always a list (may be empty) on success
    return result.data

def upsert_f1api_team_standings(standings: List[Dict[str, Any]], season: int, championship_id: str) -> List[Dict[str, Any]]:
    rows = []
    for s in standings:
        try:
            rows.append(
                {
                    "classification_id": int(s.get("classificationId") or 0),
                    "team_id": s.get("teamId") or "",
                    "season": season,
                    "championship_id": championship_id,
                    "points": int(s.get("points") or 0),
                    "position": int(s.get("position") or 0),
                    "wins": int(s.get("wins")) if s.get("wins") is not None else None,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
        except Exception as row_err:
            logging.warning("Skipping row (parse error): %s – %s", s, row_err)

    # The SDK will raise PostgrestAPIError on 409 / 400 / 500, so no need
    # to probe status_code. If we get past .execute() it was a success.
    result: APIResponse = (
        supabase.table("current_teams_standings")
        .upsert(
            rows,
            on_conflict="classification_id",
            ignore_duplicates=False,
            returning="representation",  # to get back the rows we wrote
        )
        .execute()
    )

    # result.data is always a list (may be empty) on success
    return result.data

@app.post("/api/current-drivers/f1api", tags=["Drivers"])
async def refresh_current_drivers_f1api():
    """
    Pull the latest driver list from F1 API (https://f1api.dev/api/current/drivers),
    save it to Supabase, and return what we saved.
    """
    try:
        # ------------- 1.  Fetch driver list from F1 API -------------
        async with httpx.AsyncClient() as client:
            drivers_resp = await client.get("https://f1api.dev/api/current/drivers")
            
            if drivers_resp.status_code != 200:
                raise HTTPException(502, f"F1 API returned status {drivers_resp.status_code}")
            
            response_data = drivers_resp.json()
            drivers_data = response_data.get("drivers", [])

            if not drivers_data:
                raise HTTPException(502, "F1 API returned no drivers")

        # ------------- 2.  Persist to Supabase -------------------------
        saved_rows = await asyncio.to_thread(upsert_f1api_drivers, drivers_data)

        return {
            "message": f"{len(saved_rows)} drivers saved/updated",
            "drivers": saved_rows,
            "api_metadata": {
                "season": response_data.get("season"),
                "total": response_data.get("total"),
                "championship_id": response_data.get("championshipId")
            }
        }
    
    except httpx.RequestError as e:
        raise HTTPException(502, f"Network error: {e}")
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    except Exception as e:
        # Log traceback, then re-raise as HTTPException
        import traceback, sys, logging
        logging.error("refresh_current_drivers_f1api failed\n%s",
                      "".join(traceback.format_exception(*sys.exc_info())))
        raise HTTPException(500, f"Internal error: {e}")

@app.post("/api/current-teams/f1api", tags=["Teams"])
async def refresh_current_teams_f1api():
    """
    Pull the latest teams list from F1 API (https://f1api.dev/api/current/teams),
    save it to Supabase, and return what we saved.
    """
    try:
        # ------------- 1.  Fetch teams list from F1 API -------------
        async with httpx.AsyncClient() as client:
            teams_resp = await client.get("https://f1api.dev/api/current/teams")
            
            if teams_resp.status_code != 200:
                raise HTTPException(502, f"F1 API returned status {teams_resp.status_code}")
            
            response_data = teams_resp.json()
            teams_data = response_data.get("teams", [])

        if not teams_data:
            raise HTTPException(502, "F1 API returned no teams")

        # ------------- 2.  Persist to Supabase -------------------------
        saved_rows = await asyncio.to_thread(upsert_f1api_teams, teams_data)
            
        return {
            "message": f"{len(saved_rows)} teams saved/updated",
            "teams": saved_rows,
            "api_metadata": {
                "season": response_data.get("season"),
                "total": response_data.get("total"),
                "championship_id": response_data.get("championshipId")
            }
            }
            
    except httpx.RequestError as e:
        raise HTTPException(502, f"Network error: {e}")
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    except Exception as e:
                 # Log traceback, then re-raise as HTTPException
         import traceback, sys, logging
         logging.error("refresh_current_teams_f1api failed\n%s",
                       "".join(traceback.format_exception(*sys.exc_info())))
         raise HTTPException(500, f"Internal error: {e}")

@app.get("/api/teams", tags=["Teams"])
async def get_teams():
    """Fetch all current F1 teams from Supabase database"""
    try:
        result = supabase.table("current_teams").select("*").execute()
        teams = result.data
        
        logger.info(f"Retrieved {len(teams)} teams from database")
        
        return {
            "message": f"Retrieved {len(teams)} teams",
            "teams": teams
        }
            
    except Exception as e:
        logger.error(f"Error fetching teams: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching teams: {str(e)}")

@app.post("/api/current-drivers-standings/f1api", tags=["Standings"])
async def refresh_current_drivers_standings_f1api():
    """
    Pull the latest driver championship standings from F1 API (https://f1api.dev/api/current/drivers-championship),
    save it to Supabase, and return what we saved.
    """
    try:
        # ------------- 1.  Fetch standings from F1 API -------------
        async with httpx.AsyncClient() as client:
            standings_resp = await client.get("https://f1api.dev/api/current/drivers-championship")
            
            if standings_resp.status_code != 200:
                raise HTTPException(502, f"F1 API returned status {standings_resp.status_code}")
            
            response_data = standings_resp.json()
            standings_data = response_data.get("drivers_championship", [])

        if not standings_data:
            raise HTTPException(502, "F1 API returned no driver standings")

        # Extract season and championship ID from the response
        season = response_data.get("season", 2025)
        championship_id = response_data.get("championshipId", "f1_2025")

        # ------------- 2.  Persist to Supabase -------------------------
        saved_rows = await asyncio.to_thread(upsert_f1api_driver_standings, standings_data, season, championship_id)

        return {
            "message": f"{len(saved_rows)} driver standings saved/updated",
            "standings": saved_rows,
            "api_metadata": {
                "season": season,
                "total": response_data.get("total"),
                "championship_id": championship_id
            }
        }
    
    except httpx.RequestError as e:
        raise HTTPException(502, f"Network error: {e}")
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    except Exception as e:
        # Log traceback, then re-raise as HTTPException
        import traceback, sys, logging
        logging.error("refresh_current_drivers_standings_f1api failed\n%s",
                      "".join(traceback.format_exception(*sys.exc_info())))
        raise HTTPException(500, f"Internal error: {e}")

@app.get("/api/drivers-standings", tags=["Standings"])
async def get_drivers_standings():
    """Fetch all current F1 driver championship standings from Supabase database"""
    try:
        result = supabase.table("current_drivers_standings").select("*").order("position").execute()
        standings = result.data
        
        logger.info(f"Retrieved {len(standings)} driver standings from database")
        
        return {
            "message": f"Retrieved {len(standings)} driver standings",
            "standings": standings
        }
            
    except Exception as e:
        logger.error(f"Error fetching driver standings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching driver standings: {str(e)}")

@app.post("/api/current-teams-standings/f1api", tags=["Standings"])
async def refresh_current_teams_standings_f1api():
    """
    Pull the latest constructor championship standings from F1 API (https://f1api.dev/api/current/constructors-championship),
    save it to Supabase, and return what we saved.
    """
    try:
        # ------------- 1.  Fetch standings from F1 API -------------
        async with httpx.AsyncClient() as client:
            standings_resp = await client.get("https://f1api.dev/api/current/constructors-championship")
            
            if standings_resp.status_code != 200:
                raise HTTPException(502, f"F1 API returned status {standings_resp.status_code}")
            
            response_data = standings_resp.json()
            standings_data = response_data.get("constructors_championship", [])

        if not standings_data:
            raise HTTPException(502, "F1 API returned no constructor standings")

        # Extract season and championship ID from the response
        season = response_data.get("season", 2025)
        championship_id = response_data.get("championshipId", "f1_2025")

        # ------------- 2.  Persist to Supabase -------------------------
        saved_rows = await asyncio.to_thread(upsert_f1api_team_standings, standings_data, season, championship_id)
            
        return {
            "message": f"{len(saved_rows)} team standings saved/updated",
            "standings": saved_rows,
            "api_metadata": {
                "season": season,
                "total": response_data.get("total"),
                "championship_id": championship_id
            }
            }
            
    except httpx.RequestError as e:
        raise HTTPException(502, f"Network error: {e}")
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    except Exception as e:
        # Log traceback, then re-raise as HTTPException
        import traceback, sys, logging
        logging.error("refresh_current_teams_standings_f1api failed\n%s",
                      "".join(traceback.format_exception(*sys.exc_info())))
        raise HTTPException(500, f"Internal error: {e}")

@app.get("/api/teams-standings", tags=["Standings"])
async def get_teams_standings():
    """Fetch all current F1 constructor championship standings from Supabase database"""
    try:
        result = supabase.table("current_teams_standings").select("*").order("position").execute()
        standings = result.data
        
        logger.info(f"Retrieved {len(standings)} team standings from database")
        
        return {
            "message": f"Retrieved {len(standings)} team standings",
            "standings": standings
        }
            
    except Exception as e:
        logger.error(f"Error fetching team standings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching team standings: {str(e)}")

@app.get("/api/storage/f1-ai-news")
async def get_f1_ai_news_files(date_filter: Optional[str] = None):
    """
    Fetch all files from the f1_ai_news storage bucket.
    
    Args:
        date_filter (optional): Specific date folder to fetch from (format: YYYY-MM-DD)
                               If not provided, fetches from all date folders
    
    Returns:
        Dictionary containing files organized by date folders
    """
    try:
        bucket_name = "f1_ai_news"
        
        # First, list the root directory to get date folders
        root_response = supabase.storage.from_(bucket_name).list()
        
        if not root_response:
            logger.warning(f"No folders found in bucket {bucket_name}")
            return {
                "message": "No folders found in storage",
                "bucket": bucket_name,
                "files": {},
                "total_files": 0
            }
        
        # Organize files by date folders
        files_by_date = {}
        total_files = 0
        
        # Process each folder in the root
        for folder_info in root_response:
            folder_name = folder_info.get('name', '')
            
            # Skip if it's not a folder or doesn't match date pattern
            if not folder_name or not re.match(r'^\d{4}-\d{2}-\d{2}$', folder_name):
                continue
            
            # Apply date filter if specified
            if date_filter and folder_name != date_filter:
                continue
            
            try:
                # List files in this date folder
                folder_files = supabase.storage.from_(bucket_name).list(path=folder_name)
                
                if folder_files:
                    files_by_date[folder_name] = []
                    
                    for file_info in folder_files:
                        filename = file_info.get('name', '')
                        
                        # Check if filename matches expected pattern (driverfirstname_lastname.json)
                        if filename.endswith('.json') and '_' in filename:
                            file_path = f"{folder_name}/{filename}"
                            
                            try:
                                # Get public URL for the file
                                file_url = supabase.storage.from_(bucket_name).get_public_url(file_path)
                                
                                file_data = {
                                    "filename": filename,
                                    "path": file_path,
                                    "size": file_info.get('metadata', {}).get('size', 0),
                                    "created_at": file_info.get('created_at'),
                                    "updated_at": file_info.get('updated_at'),
                                    "public_url": file_url,
                                    "driver_name": filename.replace('.json', '').replace('_', ' ')
                                }
                                
                                files_by_date[folder_name].append(file_data)
                                total_files += 1
                                
                            except Exception as file_err:
                                logger.warning(f"Error processing file {file_path}: {file_err}")
                                continue
                    
                    # Sort files within this date folder by filename
                    files_by_date[folder_name].sort(key=lambda x: x['filename'])
                
            except Exception as folder_err:
                logger.warning(f"Error processing folder {folder_name}: {folder_err}")
                continue
        
        # Sort date folders (newest first)
        sorted_files = dict(sorted(files_by_date.items(), reverse=True))
        
        logger.info(f"Retrieved {total_files} files from {len(sorted_files)} date folders in bucket {bucket_name}")
        
        return {
            "message": f"Retrieved {total_files} files from storage",
            "bucket": bucket_name,
            "date_filter": date_filter,
            "files": sorted_files,
            "total_files": total_files,
            "date_folders": list(sorted_files.keys())
        }
        
    except Exception as e:
        logger.error(f"Error fetching files from storage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching files from storage: {str(e)}")

@app.get("/api/storage/f1-ai-news/drivers/{driver_name}")
async def get_driver_news_files(driver_name: str, date_filter: Optional[str] = None):
    """
    Fetch all news files for a specific driver across all date folders.
    
    Args:
        driver_name: Driver name in format "firstname_lastname" or "firstname lastname"
        date_filter (optional): Specific date folder to search in (format: YYYY-MM-DD)
    
    Returns:
        Dictionary containing all news files for the specified driver
    """
    try:
        # Normalize driver name to filename format
        driver_filename = driver_name.replace(' ', '_') + '.json'
        
        bucket_name = "f1_ai_news"
        
        # First, list the root directory to get date folders
        root_response = supabase.storage.from_(bucket_name).list()
        
        if not root_response:
            logger.warning(f"No folders found in bucket {bucket_name}")
            return {
                "message": "No folders found in storage",
                "driver_name": driver_name,
                "driver_filename": driver_filename,
                "files": [],
                "total_files": 0
            }
        
        driver_files = []
        
        # Process each folder in the root
        for folder_info in root_response:
            folder_name = folder_info.get('name', '')
            
            # Skip if it's not a folder or doesn't match date pattern
            if not folder_name or not re.match(r'^\d{4}-\d{2}-\d{2}$', folder_name):
                continue
            
            # Apply date filter if specified
            if date_filter and folder_name != date_filter:
                continue
            
            try:
                # List files in this date folder
                folder_files = supabase.storage.from_(bucket_name).list(path=folder_name)
                
                if folder_files:
                    for file_info in folder_files:
                        filename = file_info.get('name', '')
                        
                        # Check if this is the driver's file
                        if filename == driver_filename:
                            file_path = f"{folder_name}/{filename}"
                            
                            try:
                                # Get public URL for the file
                                file_url = supabase.storage.from_(bucket_name).get_public_url(file_path)
                                
                                file_data = {
                                    "date_folder": folder_name,
                                    "filename": filename,
                                    "path": file_path,
                                    "size": file_info.get('metadata', {}).get('size', 0),
                                    "created_at": file_info.get('created_at'),
                                    "updated_at": file_info.get('updated_at'),
                                    "public_url": file_url
                                }
                                
                                driver_files.append(file_data)
                                
                            except Exception as file_err:
                                logger.warning(f"Error processing file {file_path}: {file_err}")
                                continue
                
            except Exception as folder_err:
                logger.warning(f"Error processing folder {folder_name}: {folder_err}")
                continue
        
        # Sort files by date folder (newest first)
        driver_files.sort(key=lambda x: x['date_folder'], reverse=True)
        
        logger.info(f"Retrieved {len(driver_files)} files for driver {driver_name}")
        
        return {
            "message": f"Retrieved {len(driver_files)} files for driver {driver_name}",
            "driver_name": driver_name,
            "driver_filename": driver_filename,
            "date_filter": date_filter,
            "files": driver_files,
            "total_files": len(driver_files)
        }
        
    except Exception as e:
        logger.error(f"Error fetching driver files for {driver_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching driver files: {str(e)}")

@app.get("/api/storage/f1-ai-news/{date_folder}")
async def get_f1_ai_news_files_by_date(date_folder: str):
    """
    Fetch all files from a specific date folder in the f1_ai_news storage bucket.
    
    Args:
        date_folder: Date folder to fetch from (format: YYYY-MM-DD)
    
    Returns:
        Dictionary containing files from the specified date folder
    """
    try:
        # Validate date format
        try:
            datetime.strptime(date_folder, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Use the general endpoint with date filter
        return await get_f1_ai_news_files(date_filter=date_folder)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching files for date {date_folder}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching files for date {date_folder}: {str(e)}")

@app.get("/api/storage/f1-ai-news/latest-summaries")
async def get_latest_driver_summaries():
    """
    Fetch total summaries for all drivers from the most recent date folder.
    
    Returns:
        Dictionary containing total summaries for all drivers from the latest date
    """
    try:
        bucket_name = "f1_ai_news"
        
        # First, list the root directory to get date folders
        root_response = supabase.storage.from_(bucket_name).list()
        
        if not root_response:
            logger.warning(f"No folders found in bucket {bucket_name}")
            return {
                "message": "No date folders found in storage",
                "bucket": bucket_name,
                "latest_date": None,
                "total_drivers": 0,
                "summaries": {},
                "errors": []
            }
        
        # Find the most recent date folder
        date_folders = []
        for folder_info in root_response:
            folder_name = folder_info.get('name', '')
            if folder_name and re.match(r'^\d{4}-\d{2}-\d{2}$', folder_name):
                date_folders.append(folder_name)
        
        if not date_folders:
            logger.warning(f"No valid date folders found in bucket {bucket_name}")
            return {
                "message": "No valid date folders found in storage",
                "bucket": bucket_name,
                "latest_date": None,
                "total_drivers": 0,
                "summaries": {},
                "errors": []
            }
        
        # Sort date folders and get the latest one
        date_folders.sort(reverse=True)
        latest_date = date_folders[0]
        
        logger.info(f"Latest date folder found: {latest_date}")
        
        # Use the existing endpoint to get summaries for the latest date
        return await get_all_driver_summaries_by_date(latest_date)
        
    except Exception as e:
        logger.error(f"Error fetching latest driver summaries: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching latest driver summaries: {str(e)}")

@app.get("/api/storage/f1-ai-news/{date_folder}/summaries")
async def get_all_driver_summaries_by_date(date_folder: str):
    """
    Fetch total summaries for all drivers from a specific date folder.
    
    Args:
        date_folder: Date folder to fetch from (format: YYYY-MM-DD)
    
    Returns:
        Dictionary containing total summaries for all drivers from that date
    """
    try:
        # Validate date format
        try:
            datetime.strptime(date_folder, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        bucket_name = "f1_ai_news"
        
        # List files in the specific date folder
        try:
            folder_files = supabase.storage.from_(bucket_name).list(path=date_folder)
        except Exception as folder_err:
            logger.error(f"Error listing files in folder {date_folder}: {folder_err}")
            raise HTTPException(status_code=404, detail=f"Date folder {date_folder} not found or error accessing it")
        
        if not folder_files:
            logger.warning(f"No files found in date folder {date_folder}")
            return {
                "message": f"No files found in date folder {date_folder}",
                "date_folder": date_folder,
                "total_drivers": 0,
                "summaries": {},
                "errors": []
            }
        
        summaries = {}
        errors = []
        total_drivers = 0
        
        # Process each JSON file in the date folder
        for file_info in folder_files:
            filename = file_info.get('name', '')
            
            # Check if filename matches expected pattern (driverfirstname_lastname.json)
            if filename.endswith('.json') and '_' in filename:
                file_path = f"{date_folder}/{filename}"
                driver_name = filename.replace('.json', '')
                
                try:
                    # Download and parse the JSON file
                    file_content = supabase.storage.from_(bucket_name).download(file_path)
                    json_data = json.loads(file_content.decode('utf-8'))
                    
                    # Extract total summary from the JSON
                    total_summary = json_data.get('total_summary', '')
                    
                    if total_summary:
                        summaries[f"{driver_name}_total_summary"] = total_summary
                        total_drivers += 1
                    else:
                        errors.append(f"No total_summary found in {filename}")
                        
                except json.JSONDecodeError as json_err:
                    error_msg = f"Invalid JSON in {filename}: {str(json_err)}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
                except Exception as file_err:
                    error_msg = f"Error processing {filename}: {str(file_err)}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
        
        # Sort summaries by driver name for consistent ordering
        sorted_summaries = dict(sorted(summaries.items()))
        
        logger.info(f"Retrieved summaries for {total_drivers} drivers from date folder {date_folder}")
        
        return {
            "message": f"Retrieved summaries for {total_drivers} drivers from {date_folder}",
            "date_folder": date_folder,
            "total_drivers": total_drivers,
            "summaries": sorted_summaries,
            "errors": errors if errors else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching driver summaries for date {date_folder}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching driver summaries: {str(e)}")

@app.get("/api/storage/f1-ai-news/{date_folder}/{filename}")
async def get_f1_ai_news_file_content(date_folder: str, filename: str):
    """
    Fetch the content of a specific file from the f1_ai_news storage bucket.
    
    Args:
        date_folder: Date folder (format: YYYY-MM-DD)
        filename: Name of the file (e.g., driverfirstname_lastname.json)
    
    Returns:
        The file content as JSON
    """
    try:
        # Validate date format
        try:
            datetime.strptime(date_folder, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Validate filename format
        if not filename.endswith('.json') or '_' not in filename:
            raise HTTPException(status_code=400, detail="Invalid filename format. Expected: driverfirstname_lastname.json")
        
        bucket_name = "f1_ai_news"
        file_path = f"{date_folder}/{filename}"
        
        try:
            # Download the file content
            file_content = supabase.storage.from_(bucket_name).download(file_path)
            
            # Parse JSON content
            try:
                json_data = json.loads(file_content.decode('utf-8'))
                return {
                    "message": "File content retrieved successfully",
                    "date_folder": date_folder,
                    "filename": filename,
                    "driver_name": filename.replace('.json', '').replace('_', ' '),
                    "content": json_data,
                    "file_size": len(file_content)
                }
            except json.JSONDecodeError as json_err:
                raise HTTPException(status_code=500, detail=f"Invalid JSON content in file: {str(json_err)}")
                
        except Exception as download_err:
            logger.error(f"Error downloading file {file_path}: {download_err}")
            raise HTTPException(status_code=404, detail=f"File not found or error downloading: {str(download_err)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching file content for {date_folder}/{filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching file content: {str(e)}")
async def get_latest_driver_summaries():
    """
    Fetch total summaries for all drivers from the most recent date folder.
    
    Returns:
        Dictionary containing total summaries for all drivers from the latest date
    """
    try:
        bucket_name = "f1_ai_news"
        
        # First, list the root directory to get date folders
        root_response = supabase.storage.from_(bucket_name).list()
        
        if not root_response:
            logger.warning(f"No folders found in bucket {bucket_name}")
            return {
                "message": "No date folders found in storage",
                "bucket": bucket_name,
                "latest_date": None,
                "total_drivers": 0,
                "summaries": {},
                "errors": []
            }
        
        # Find the most recent date folder
        date_folders = []
        for folder_info in root_response:
            folder_name = folder_info.get('name', '')
            if folder_name and re.match(r'^\d{4}-\d{2}-\d{2}$', folder_name):
                date_folders.append(folder_name)
        
        if not date_folders:
            logger.warning(f"No valid date folders found in bucket {bucket_name}")
            return {
                "message": "No valid date folders found in storage",
                "bucket": bucket_name,
                "latest_date": None,
                "total_drivers": 0,
                "summaries": {},
                "errors": []
            }
        
        # Sort date folders and get the latest one
        date_folders.sort(reverse=True)
        latest_date = date_folders[0]
        
        logger.info(f"Latest date folder found: {latest_date}")
        
        # Use the existing endpoint to get summaries for the latest date
        return await get_all_driver_summaries_by_date(latest_date)
        
    except Exception as e:
        logger.error(f"Error fetching latest driver summaries: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching latest driver summaries: {str(e)}")

@app.get("/api/storage/f1-ai-news/{date_folder}/summaries")
async def get_all_driver_summaries_by_date(date_folder: str):
    """
    Fetch total summaries for all drivers from a specific date folder.
    
    Args:
        date_folder: Date folder to fetch from (format: YYYY-MM-DD)
    
    Returns:
        Dictionary containing total summaries for all drivers from that date
    """
    try:
        # Validate date format
        try:
            datetime.strptime(date_folder, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        bucket_name = "f1_ai_news"
        
        # List files in the specific date folder
        try:
            folder_files = supabase.storage.from_(bucket_name).list(path=date_folder)
        except Exception as folder_err:
            logger.error(f"Error listing files in folder {date_folder}: {folder_err}")
            raise HTTPException(status_code=404, detail=f"Date folder {date_folder} not found or error accessing it")
        
        if not folder_files:
            logger.warning(f"No files found in date folder {date_folder}")
            return {
                "message": f"No files found in date folder {date_folder}",
                "date_folder": date_folder,
                "total_drivers": 0,
                "summaries": {},
                "errors": []
            }
        
        summaries = {}
        errors = []
        total_drivers = 0
        
        # Process each JSON file in the date folder
        for file_info in folder_files:
            filename = file_info.get('name', '')
            
            # Check if filename matches expected pattern (driverfirstname_lastname.json)
            if filename.endswith('.json') and '_' in filename:
                file_path = f"{date_folder}/{filename}"
                driver_name = filename.replace('.json', '')
                
                try:
                    # Download and parse the JSON file
                    file_content = supabase.storage.from_(bucket_name).download(file_path)
                    json_data = json.loads(file_content.decode('utf-8'))
                    
                    # Extract total summary from the JSON
                    total_summary = json_data.get('total_summary', '')
                    
                    if total_summary:
                        summaries[f"{driver_name}_total_summary"] = total_summary
                        total_drivers += 1
                    else:
                        errors.append(f"No total_summary found in {filename}")
                        
                except json.JSONDecodeError as json_err:
                    error_msg = f"Invalid JSON in {filename}: {str(json_err)}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
                except Exception as file_err:
                    error_msg = f"Error processing {filename}: {str(file_err)}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
        
        # Sort summaries by driver name for consistent ordering
        sorted_summaries = dict(sorted(summaries.items()))
        
        logger.info(f"Retrieved summaries for {total_drivers} drivers from date folder {date_folder}")
        
        return {
            "message": f"Retrieved summaries for {total_drivers} drivers from {date_folder}",
            "date_folder": date_folder,
            "total_drivers": total_drivers,
            "summaries": sorted_summaries,
            "errors": errors if errors else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching driver summaries for date {date_folder}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching driver summaries: {str(e)}")
    """
    Fetch total summaries for all drivers from the most recent date folder.
    
    Returns:
        Dictionary containing total summaries for all drivers from the latest date
    """
    try:
        bucket_name = "f1_ai_news"
        
        # First, list the root directory to get date folders
        root_response = supabase.storage.from_(bucket_name).list()
        
        if not root_response:
            logger.warning(f"No folders found in bucket {bucket_name}")
            return {
                "message": "No date folders found in storage",
                "bucket": bucket_name,
                "latest_date": None,
                "total_drivers": 0,
                "summaries": {},
                "errors": []
            }
        
        # Find the most recent date folder
        date_folders = []
        for folder_info in root_response:
            folder_name = folder_info.get('name', '')
            if folder_name and re.match(r'^\d{4}-\d{2}-\d{2}$', folder_name):
                date_folders.append(folder_name)
        
        if not date_folders:
            logger.warning(f"No valid date folders found in bucket {bucket_name}")
            return {
                "message": "No valid date folders found in storage",
                "bucket": bucket_name,
                "latest_date": None,
                "total_drivers": 0,
                "summaries": {},
                "errors": []
            }
        
        # Sort date folders and get the latest one
        date_folders.sort(reverse=True)
        latest_date = date_folders[0]
        
        logger.info(f"Latest date folder found: {latest_date}")
        
        # Use the existing endpoint to get summaries for the latest date
        return await get_all_driver_summaries_by_date(latest_date)
        
    except Exception as e:
        logger.error(f"Error fetching latest driver summaries: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching latest driver summaries: {str(e)}")

@app.get("/api/storage/f1-ai-news/drivers/{driver_name}")
async def get_driver_news_files(driver_name: str, date_filter: Optional[str] = None):
    """
    Fetch all news files for a specific driver across all date folders.
    
    Args:
        driver_name: Driver name in format "firstname_lastname" or "firstname lastname"
        date_filter (optional): Specific date folder to search in (format: YYYY-MM-DD)
    
    Returns:
        Dictionary containing all news files for the specified driver
    """
    try:
        # Normalize driver name to filename format
        driver_filename = driver_name.replace(' ', '_') + '.json'
        
        bucket_name = "f1_ai_news"
        
        # First, list the root directory to get date folders
        root_response = supabase.storage.from_(bucket_name).list()
        
        if not root_response:
            logger.warning(f"No folders found in bucket {bucket_name}")
            return {
                "message": "No folders found in storage",
                "driver_name": driver_name,
                "driver_filename": driver_filename,
                "files": [],
                "total_files": 0
            }
        
        driver_files = []
        
        # Process each folder in the root
        for folder_info in root_response:
            folder_name = folder_info.get('name', '')
            
            # Skip if it's not a folder or doesn't match date pattern
            if not folder_name or not re.match(r'^\d{4}-\d{2}-\d{2}$', folder_name):
                continue
            
            # Apply date filter if specified
            if date_filter and folder_name != date_filter:
                continue
            
            try:
                # List files in this date folder
                folder_files = supabase.storage.from_(bucket_name).list(path=folder_name)
                
                if folder_files:
                    for file_info in folder_files:
                        filename = file_info.get('name', '')
                        
                        # Check if this is the driver's file
                        if filename == driver_filename:
                            file_path = f"{folder_name}/{filename}"
                            
                            try:
                                # Get public URL for the file
                                file_url = supabase.storage.from_(bucket_name).get_public_url(file_path)
                                
                                file_data = {
                                    "date_folder": folder_name,
                                    "filename": filename,
                                    "path": file_path,
                                    "size": file_info.get('metadata', {}).get('size', 0),
                                    "created_at": file_info.get('created_at'),
                                    "updated_at": file_info.get('updated_at'),
                                    "public_url": file_url
                                }
                                
                                driver_files.append(file_data)
                                
                            except Exception as file_err:
                                logger.warning(f"Error processing file {file_path}: {file_err}")
                                continue
                
            except Exception as folder_err:
                logger.warning(f"Error processing folder {folder_name}: {folder_err}")
                continue
        
        # Sort files by date folder (newest first)
        driver_files.sort(key=lambda x: x['date_folder'], reverse=True)
        
        logger.info(f"Retrieved {len(driver_files)} files for driver {driver_name}")
        
        return {
            "message": f"Retrieved {len(driver_files)} files for driver {driver_name}",
            "driver_name": driver_name,
            "driver_filename": driver_filename,
            "date_filter": date_filter,
            "files": driver_files,
            "total_files": len(driver_files)
        }
        
    except Exception as e:
        logger.error(f"Error fetching driver files for {driver_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching driver files: {str(e)}")
