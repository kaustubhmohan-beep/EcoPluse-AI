"""
EcoPulse AI - Time-of-Use (ToU) Tariff Cost & Appliance Load Scheduling Tool
Calculates electricity cost differentials between Flat Standard and Dynamic Time-of-Use
tariffs, identifying optimal load-shifting windows for high-power appliances.
"""

import logging
from typing import Dict, Any, Optional, List
from src.data_engine import data_engine

logger = logging.getLogger("ecopulse.tariff_tool")

class TariffTool:
    def __init__(self):
        # UK / London Tariff Rate Structures (£ / kWh)
        self.flat_rate = 0.18  # Flat Standard rate: 18p/kWh

        self.tou_rates = {
            "off_peak": {"rate": 0.08, "slots": [(0, 7), (23, 24)], "label": "Off-Peak (Green Window)"},
            "standard": {"rate": 0.16, "slots": [(7, 16), (19, 23)], "label": "Standard (Normal Window)"},
            "peak_surge": {"rate": 0.38, "slots": [(16, 19)], "label": "Peak Surge (Red Window)"}
        }

        # Appliance default profiles (Power in kW, typical duration in hours)
        self.appliance_profiles = {
            "ev_charger": {"name": "Electric Vehicle (EV) Charging", "kw": 7.2, "duration": 4.0},
            "heat_pump": {"name": "Heat Pump / Space Heating", "kw": 3.5, "duration": 3.0},
            "washing_machine": {"name": "Washing Machine & Dryer Cycle", "kw": 2.2, "duration": 1.5},
            "dishwasher": {"name": "Eco Dishwasher Cycle", "kw": 1.8, "duration": 1.5},
            "water_heater": {"name": "Immersion Water Heater", "kw": 3.0, "duration": 2.0},
            "general": {"name": "Heavy Electrical Load", "kw": 2.0, "duration": 2.0}
        }

    def calculate_tariff_cost_and_schedule(
        self,
        household_id: Optional[str] = None,
        appliance_type: str = "ev_charger",
        power_draw_kw: Optional[float] = None,
        duration_hours: Optional[float] = None,
        target_date: str = "2026-08-15"
    ) -> Dict[str, Any]:
        """
        Calculates exact costs across Peak, Standard, and Off-Peak windows,
        and generates an optimized load-shifting schedule.
        """
        # Resolve household tariff type if household_id provided
        tariff_type = "ToU"
        if household_id:
            profile = data_engine.get_household_profile(household_id)
            if profile:
                tariff_type = profile.get("tariff_type", "ToU")

        # Resolve appliance specifications
        preset = self.appliance_profiles.get(appliance_type.lower(), self.appliance_profiles["general"])
        kw = float(power_draw_kw) if power_draw_kw is not None and power_draw_kw > 0 else preset["kw"]
        dur = float(duration_hours) if duration_hours is not None and duration_hours > 0 else preset["duration"]
        total_kwh = round(kw * dur, 3)

        # Calculate costs across windows
        peak_rate = self.tou_rates["peak_surge"]["rate"]
        off_peak_rate = self.tou_rates["off_peak"]["rate"]
        standard_rate = self.tou_rates["standard"]["rate"]

        cost_peak = round(total_kwh * peak_rate, 2)
        cost_off_peak = round(total_kwh * off_peak_rate, 2)
        cost_standard = round(total_kwh * standard_rate, 2)
        cost_flat = round(total_kwh * self.flat_rate, 2)

        # Financial Arbitrage Savings
        savings_vs_peak = round(cost_peak - cost_off_peak, 2)
        savings_vs_flat = round(cost_flat - cost_off_peak, 2)
        savings_pct = round((savings_vs_peak / (cost_peak + 1e-5)) * 100, 1)

        # Annualized savings if run 3 times a week (156 cycles/year)
        annual_savings_gbp = round(savings_vs_peak * 156, 2)

        # Generate Timeline Windows
        schedule_recommendation = {
            "optimal_window": {
                "window_name": "Off-Peak Night Slot (Recommended)",
                "time_range": "01:00 - 05:00",
                "rate_per_kwh": f"£{off_peak_rate:.2f}",
                "total_run_cost": f"£{cost_off_peak:.2f}",
                "status": "OPTIMAL_GREEN"
            },
            "alternative_window": {
                "window_name": "Mid-Day Solar / Shoulder Slot",
                "time_range": "11:00 - 15:00",
                "rate_per_kwh": f"£{standard_rate:.2f}",
                "total_run_cost": f"£{cost_standard:.2f}",
                "status": "ACCEPTABLE_YELLOW"
            },
            "restricted_window": {
                "window_name": "Evening Peak Grid Surge (Avoid)",
                "time_range": "16:00 - 19:00",
                "rate_per_kwh": f"£{peak_rate:.2f}",
                "total_run_cost": f"£{cost_peak:.2f}",
                "status": "PENALTY_RED"
            }
        }

        actionable_advice = (
            f"By shifting your {preset['name']} ({total_kwh} kWh) from evening peak hours (16:00-19:00) "
            f"to the off-peak window (01:00-05:00), you will save £{savings_vs_peak:.2f} per cycle ({savings_pct}% cost reduction). "
            f"Over a year (156 cycles), this habit shifts £{annual_savings_gbp:.2f} back into your wallet while relieving grid stress."
        )

        return {
            "status": "success",
            "appliance": {
                "type": appliance_type,
                "name": preset["name"],
                "power_draw_kw": kw,
                "duration_hours": dur,
                "total_energy_kwh": total_kwh
            },
            "tariff_context": {
                "active_tariff": tariff_type,
                "flat_rate_gbp_per_kwh": self.flat_rate,
                "tou_rates": {
                    "off_peak": off_peak_rate,
                    "standard": standard_rate,
                    "peak_surge": peak_rate
                }
            },
            "cost_breakdown": {
                "cost_if_run_in_peak_gbp": cost_peak,
                "cost_if_run_in_standard_gbp": cost_standard,
                "cost_if_run_in_off_peak_gbp": cost_off_peak,
                "cost_under_flat_tariff_gbp": cost_flat,
                "single_cycle_savings_gbp": savings_vs_peak,
                "savings_percentage": savings_pct,
                "annualized_projected_savings_gbp": annual_savings_gbp
            },
            "schedule": schedule_recommendation,
            "actionable_advice": actionable_advice
        }

# Global singleton instance
tariff_tool = TariffTool()
