"""
EcoPulse AI - FastAPI Backend Server
Provides REST API endpoints for the conversational agent, household analytics,
weather data, and real-time tariff optimization.
"""

import os
import sys
import json
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

# Ensure src/ is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.agent import agent
from src.data_engine import data_engine
from src.tools.weather_tool import weather_tool
from src.tools.tariff_tool import tariff_tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ecopulse.app")

app = FastAPI(
    title="EcoPulse AI Energy Intelligence API",
    description="Intelligent energy analytics, weather-correlated demand forecasting, and ToU tariff optimization for UK smart meter households.",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# REQUEST / RESPONSE MODELS
# ─────────────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    household_id: Optional[str] = None

class TariffSimulateRequest(BaseModel):
    household_id: Optional[str] = None
    appliance_type: str = "ev_charger"
    power_draw_kw: Optional[float] = None
    duration_hours: Optional[float] = None
    target_date: str = "2026-08-15"


# ─────────────────────────────────────────────────────────────────────────────
# API ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "online",
        "service": "EcoPulse AI Energy Intelligence Platform",
        "version": "1.0.0",
        "tools": ["smart_meter_analytics", "weather_forecast", "tariff_optimizer", "rag_knowledge"]
    }


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Main conversational agent endpoint.
    Accepts a user message and optional household ID.
    Returns a comprehensive markdown-formatted diagnostic response.
    """
    if not request.message or len(request.message.strip()) < 3:
        raise HTTPException(status_code=400, detail="Message must be at least 3 characters.")

    try:
        response = agent.process(
            message=request.message,
            household_id=request.household_id
        )
        return {
            "status": "success",
            "response": response,
            "household_id": request.household_id
        }
    except Exception as e:
        logger.error(f"Chat processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Agent processing error: {str(e)}")


@app.get("/api/household/{lclid}/overview")
async def get_household_overview(
    lclid: str,
    start_date: str = Query("2013-01-01", description="Start date YYYY-MM-DD"),
    end_date: str = Query("2013-01-14", description="End date YYYY-MM-DD")
):
    """Returns a complete household energy profile with demographics and consumption stats."""
    profile = data_engine.get_household_profile(lclid.upper())
    if not profile:
        raise HTTPException(status_code=404, detail=f"Household '{lclid}' not found.")

    daily_data = data_engine.query_daily_consumption(lclid.upper(), start_date, end_date)
    cohort_stats = data_engine.get_cohort_benchmark(profile["acorn_group"], end_date)

    return {
        "household": profile,
        "daily_readings": daily_data,
        "cohort_benchmark": cohort_stats
    }


@app.get("/api/household/{lclid}/half-hourly")
async def get_half_hourly(
    lclid: str,
    start_date: str = Query("2013-01-01"),
    end_date: str = Query("2013-01-03")
):
    """Returns 30-minute granular diurnal load curve data for visualization."""
    data = data_engine.query_half_hourly_readings(lclid.upper(), start_date, end_date)
    if not data:
        raise HTTPException(status_code=404, detail=f"No half-hourly data found for {lclid} in specified range.")
    return {"household_id": lclid, "data": data}


@app.get("/api/household/sample")
async def get_sample_households(limit: int = Query(10, ge=1, le=50)):
    """Returns a diverse sample of household profiles for the UI explorer."""
    samples = data_engine.get_sample_households(limit=limit)
    return {"households": samples, "count": len(samples)}


@app.get("/api/weather/forecast")
async def get_weather(
    lat: float = Query(51.5074, description="Latitude"),
    lon: float = Query(-0.1278, description="Longitude"),
    target_date: Optional[str] = Query(None, description="Target date YYYY-MM-DD"),
    hours_ahead: int = Query(24, ge=1, le=48)
):
    """Fetches weather forecast with energy thermal stress analysis."""
    result = weather_tool.get_weather_forecast(
        latitude=lat,
        longitude=lon,
        forecast_type="hourly",
        target_date=target_date,
        hours_ahead=hours_ahead
    )
    return result


@app.post("/api/simulate/tariff")
async def simulate_tariff(request: TariffSimulateRequest):
    """Calculates cost and optimal scheduling window for an appliance."""
    result = tariff_tool.calculate_tariff_cost_and_schedule(
        household_id=request.household_id,
        appliance_type=request.appliance_type,
        power_draw_kw=request.power_draw_kw,
        duration_hours=request.duration_hours,
        target_date=request.target_date
    )
    return result


@app.get("/api/tariff/windows")
async def get_tariff_windows():
    """Returns current ToU tariff rate windows."""
    return {
        "off_peak": {"rate_gbp_per_kwh": 0.08, "windows": "00:00-07:00 & 23:00-24:00", "label": "Green (Cheapest)"},
        "standard": {"rate_gbp_per_kwh": 0.16, "windows": "07:00-16:00 & 19:00-23:00", "label": "Normal"},
        "peak_surge": {"rate_gbp_per_kwh": 0.38, "windows": "16:00-19:00", "label": "Red (Most Expensive)"}
    }


# ─────────────────────────────────────────────────────────────────────────────
# STATIC FILE HOSTING
# ─────────────────────────────────────────────────────────────────────────────
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serves the main web dashboard HTML."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>EcoPulse AI - Static files not found. Please check /static directory.</h1>")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
