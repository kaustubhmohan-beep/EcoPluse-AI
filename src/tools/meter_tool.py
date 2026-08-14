"""
EcoPulse AI - Smart Meter Telemetry Analytics Tool
Performs time-series aggregation, diurnal 48-slot load disaggregation,
overnight vampire load detection, anomaly identification, and ACORN cohort benchmarking.
"""

import logging
from typing import Dict, Any, Optional, List
import numpy as np
from src.data_engine import data_engine

logger = logging.getLogger("ecopulse.meter_tool")

class MeterTool:
    def __init__(self):
        pass

    def analyze_smart_meter_consumption(
        self,
        household_id: str,
        start_date: str = "2013-01-01",
        end_date: str = "2013-01-15",
        granularity: str = "half_hourly",
        detect_anomalies: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieves smart meter time-series data and computes:
        - Total, daily average, median, and peak consumption.
        - Diurnal profile disaggregation (Overnight baseline, morning peak, evening peak).
        - Overnight vampire draw analysis.
        - ACORN demographic cohort benchmarking.
        - Statistical anomaly detection (>2 std deviations above baseline).
        """
        profile = data_engine.get_household_profile(household_id)
        if not profile:
            return {
                "status": "error",
                "message": f"Household '{household_id}' not found in database. Please check the LCLid."
            }

        daily_data = data_engine.query_daily_consumption(household_id, start_date, end_date)
        half_hourly_data = data_engine.query_half_hourly_readings(household_id, start_date, end_date)

        if not daily_data and not half_hourly_data:
            return {
                "status": "warning",
                "message": f"No meter readings found for household {household_id} between {start_date} and {end_date}.",
                "profile": profile
            }

        # Daily aggregate statistics
        daily_sums = [d["energy_sum_kwh"] for d in daily_data] if daily_data else [h["daily_total_kwh"] for h in half_hourly_data]
        total_kwh = round(sum(daily_sums), 2)
        mean_daily_kwh = round(float(np.mean(daily_sums)), 2) if daily_sums else 0.0
        median_daily_kwh = round(float(np.median(daily_sums)), 2) if daily_sums else 0.0
        max_daily_kwh = round(float(np.max(daily_sums)), 2) if daily_sums else 0.0
        min_daily_kwh = round(float(np.min(daily_sums)), 2) if daily_sums else 0.0
        std_daily_kwh = round(float(np.std(daily_sums)), 2) if len(daily_sums) > 1 else 0.0

        # Disaggregate Diurnal Profiles from half-hourly data
        diurnal_breakdown = {}
        anomalies = []
        avg_overnight_draw = 0.0
        avg_evening_peak = 0.0

        if half_hourly_data:
            overnight_baselines = [h["overnight_baseline_avg_kwh"] for h in half_hourly_data]
            evening_peaks = [h["evening_peak_avg_kwh"] for h in half_hourly_data]
            avg_overnight_draw = round(float(np.mean(overnight_baselines)), 3)
            avg_evening_peak = round(float(np.mean(evening_peaks)), 3)

            # 48-slot average curve across the selected period
            all_slots = np.array([h["half_hourly_slots_kwh"] for h in half_hourly_data])
            slot_averages = np.round(np.mean(all_slots, axis=0), 4).tolist()

            diurnal_breakdown = {
                "average_48_slots_kwh": slot_averages,
                "overnight_vampire_baseline_kwh": avg_overnight_draw,
                "evening_peak_window_avg_kwh": avg_evening_peak,
                "peak_to_base_ratio": round(avg_evening_peak / (avg_overnight_draw + 1e-5), 2)
            }

            if detect_anomalies:
                threshold = mean_daily_kwh + (2.0 * std_daily_kwh) if std_daily_kwh > 0 else mean_daily_kwh * 1.5
                for h in half_hourly_data:
                    # Check daily spike
                    if h["daily_total_kwh"] > threshold and threshold > 0:
                        anomalies.append({
                            "date": h["date"],
                            "type": "DAILY_CONSUMPTION_SURGE",
                            "severity": "HIGH" if h["daily_total_kwh"] > threshold * 1.3 else "MODERATE",
                            "observed_kwh": h["daily_total_kwh"],
                            "expected_kwh": mean_daily_kwh,
                            "diagnosis": "Unusually heavy continuous load detected. Correlate with extreme cold weather or simultaneous heavy appliance usage."
                        })
                    # Check overnight baseline leak (>0.25 kWh continuously between 00:00 and 05:30)
                    if h["overnight_baseline_avg_kwh"] > 0.25:
                        anomalies.append({
                            "date": h["date"],
                            "type": "ELEVATED_VAMPIRE_STANDBY_LOAD",
                            "severity": "MEDIUM",
                            "observed_kwh": h["overnight_baseline_avg_kwh"],
                            "expected_kwh": 0.08,
                            "diagnosis": "Continuous overnight draw exceeds standard standby limit. Inspect refrigerator door gasket seals, dehumidifiers, or always-on desktop computers."
                        })

        # Cohort Benchmark
        ref_date = daily_data[-1]["date"] if daily_data else start_date
        cohort_stats = data_engine.get_cohort_benchmark(profile["acorn_group"], ref_date)
        cohort_diff_pct = round(((mean_daily_kwh - cohort_stats["mean_kwh"]) / (cohort_stats["mean_kwh"] + 1e-5)) * 100, 1)

        return {
            "status": "success",
            "household": {
                "household_id": household_id,
                "tariff_type": profile["tariff_type"],
                "acorn_code": profile["acorn"],
                "acorn_group": profile["acorn_group"]
            },
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "days_analyzed": len(daily_sums)
            },
            "summary_metrics": {
                "total_consumption_kwh": total_kwh,
                "mean_daily_kwh": mean_daily_kwh,
                "median_daily_kwh": median_daily_kwh,
                "max_daily_kwh": max_daily_kwh,
                "min_daily_kwh": min_daily_kwh,
                "daily_std_kwh": std_daily_kwh,
                "overnight_baseline_kwh": avg_overnight_draw,
                "evening_peak_kwh": avg_evening_peak
            },
            "cohort_benchmark": {
                "cohort_name": profile["acorn_group"],
                "cohort_mean_kwh": cohort_stats["mean_kwh"],
                "cohort_median_kwh": cohort_stats["median_kwh"],
                "household_vs_cohort_diff_pct": cohort_diff_pct,
                "relative_standing": "ABOVE_AVERAGE_CONSUMER" if cohort_diff_pct > 10 else ("BELOW_AVERAGE_EFFICIENT" if cohort_diff_pct < -10 else "ON_PAR_WITH_COHORT")
            },
            "diurnal_breakdown": diurnal_breakdown,
            "anomalies_detected": anomalies,
            "daily_readings": daily_data
        }

# Global singleton
meter_tool = MeterTool()
