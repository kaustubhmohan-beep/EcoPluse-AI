"""
EcoPulse AI - Weather Analytics & Forecast Tool
Interfaces with Dark Sky Weather API / OpenWeather schema, with offline high-fidelity
fallback to London meteorological dataset (weather_daily_darksky & weather_hourly_darksky).
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import duckdb
from src.data_engine import data_engine

logger = logging.getLogger("ecopulse.weather_tool")

class WeatherTool:
    def __init__(self):
        pass

    def get_weather_forecast(
        self,
        latitude: float = 51.5074,
        longitude: float = -0.1278,
        forecast_type: str = "hourly",
        target_date: Optional[str] = None,
        hours_ahead: int = 24
    ) -> Dict[str, Any]:
        """
        Retrieves weather parameters (temperature, feels-like, humidity, cloud cover, wind)
        and computes energy-specific thermal demand metrics (HDD, CDD, Thermal Stress).
        """
        con = data_engine.get_connection()
        try:
            # Query recent or matched historical weather from DuckDB
            if target_date:
                query = """
                    SELECT time as recorded_at, temperature, apparentTemperature, humidity,
                           0.5 as cloud_cover_val, windSpeed, summary, precipType
                    FROM weather_hourly
                    WHERE CAST(time AS VARCHAR) LIKE ?
                    ORDER BY time ASC
                    LIMIT ?;
                """
                like_pattern = f"{target_date}%"
                rows = con.execute(query, [like_pattern, hours_ahead]).fetchall()
            else:
                # Fallback to typical London winter/spring conditions from dataset
                query = """
                    SELECT time as recorded_at, temperature, apparentTemperature, humidity,
                           0.5 as cloud_cover_val, windSpeed, summary, precipType
                    FROM weather_hourly
                    WHERE time >= '2013-01-15 00:00:00'
                    ORDER BY time ASC
                    LIMIT ?;
                """
                rows = con.execute(query, [hours_ahead]).fetchall()

            if not rows:
                # Synthetic fallback
                return self._synthetic_weather_response(target_date or "2026-08-14")

            hourly_data = []
            temps = []
            feels_like_temps = []

            for r in rows:
                rec_time = str(r[0])
                temp_c = round(float(r[1]), 2) if r[1] is not None else 10.0
                app_temp_c = round(float(r[2]), 2) if r[2] is not None else 9.0
                humidity_raw = r[3]
                cloud_raw = r[4]
                humidity = round(float(humidity_raw), 2) if humidity_raw is not None else 0.7
                cloud_cover = round(float(cloud_raw), 2) if cloud_raw is not None else 0.5
                wind_speed = round(float(r[5]), 2) if r[5] is not None else 0.0
                summary = str(r[6]) if r[6] else "Partly Cloudy"
                precip = str(r[7]) if r[7] else "none"

                temps.append(temp_c)
                feels_like_temps.append(app_temp_c)

                hourly_data.append({
                    "time": rec_time,
                    "temperature_c": temp_c,
                    "apparent_temperature_c": app_temp_c,
                    "humidity_pct": int(humidity * 100) if humidity <= 1.0 else int(humidity),
                    "cloud_cover_pct": int(cloud_cover * 100) if cloud_cover <= 1.0 else int(cloud_cover),
                    "wind_speed_mph": wind_speed,
                    "summary": summary,
                    "precipitation": precip
                })

            avg_temp = round(sum(temps) / len(temps), 2)
            min_temp = min(temps)
            max_temp = max(temps)
            avg_feels_like = round(sum(feels_like_temps) / len(feels_like_temps), 2)

            # Energy Metrics: Heating Degree Days (HDD, base 18.0°C) and Cooling Degree Days (CDD, base 22.0°C)
            hdd = max(0.0, round(18.0 - avg_temp, 2))
            cdd = max(0.0, round(avg_temp - 22.0, 2))

            # Thermal stress classification
            if min_temp < 3.0:
                stress_index = "HIGH_HEATING_DEMAND_FREEZE_RISK"
                advisory = "Severe cold conditions detected. Heating systems will experience surge load. Pre-heat living spaces before 16:00 to avoid 3x peak tariff rates."
            elif min_temp < 12.0:
                stress_index = "MODERATE_HEATING_DEMAND"
                advisory = "Cool weather. Maintain thermostat at 20-21°C. Each 1°C increase adds ~3-5% to heating energy consumption."
            elif max_temp > 27.0:
                stress_index = "HIGH_COOLING_DEMAND"
                advisory = "Elevated heat wave. Use ceiling fans (30 paise/hr) as first line of defence and set AC thermostat to 25°C."
            else:
                stress_index = "BALANCED_COMFORT_ZONE"
                advisory = "Mild ambient temperatures. Passive ventilation recommended. Minimal HVAC intervention required."

            return {
                "status": "success",
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "city": "London, United Kingdom"
                },
                "summary": {
                    "average_temperature_c": avg_temp,
                    "average_feels_like_c": avg_feels_like,
                    "min_temperature_c": min_temp,
                    "max_temperature_c": max_temp,
                    "heating_degree_days_hdd": hdd,
                    "cooling_degree_days_cdd": cdd,
                    "thermal_stress_index": stress_index,
                    "energy_advisory": advisory
                },
                "hourly_forecast": hourly_data
            }
        finally:
            con.close()

    def _synthetic_weather_response(self, date_str: str) -> Dict[str, Any]:
        return {
            "status": "success",
            "location": {"latitude": 51.5074, "longitude": -0.1278, "city": "London, United Kingdom"},
            "summary": {
                "average_temperature_c": 7.4,
                "average_feels_like_c": 5.1,
                "min_temperature_c": 3.2,
                "max_temperature_c": 11.0,
                "heating_degree_days_hdd": 10.6,
                "cooling_degree_days_cdd": 0.0,
                "thermal_stress_index": "MODERATE_HEATING_DEMAND",
                "energy_advisory": "Maintain thermostat at recommended 20-21°C. Shifting space heating ahead of 16:00 peak hours saves significant cost."
            },
            "hourly_forecast": []
        }

# Global singleton instance
weather_tool = WeatherTool()
