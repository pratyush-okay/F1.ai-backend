# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
from typing import List, Dict, Any
import asyncio
import re
import os
import logging
from supabase import create_client, Client
from postgrest import APIResponse
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path

load_dotenv(dotenv_path=Path(".env.dev"))

# Supabase client
SUPABASE_DEV_URL = os.getenv("SUPABASE_DEV_URL") or os.getenv("SUPABASE_URL")
SUPABASE_DEV_KEY = os.getenv("SUPABASE_DEV_KEY") or os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_DEV_URL, SUPABASE_DEV_KEY)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(title="Formula1.ai API", description="F1 data API using OpenF1")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "https://your-frontend-domain.com",  # Add your production frontend URL
        # Add Railway frontend URL when you know it
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
            ignore_duplicates=True,
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
            ignore_duplicates=True,
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
