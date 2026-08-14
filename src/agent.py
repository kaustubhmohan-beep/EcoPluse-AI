"""
EcoPulse AI - Core Agent Orchestrator (v2 — Precise Intent & Dispatch)

Key improvements over v1:
 - Added 'calculation' intent to handle energy math queries (E = P × t / 1000).
 - Weather tool ONLY fires for explicit weather/forecast/climate queries.
 - Tariff tool ONLY fires for explicit scheduling/tariff/EV queries.
 - RAG category is tightly matched to the SPECIFIC appliance or topic in the query.
 - Generic "action items" footer is ONLY appended for relevant intents, not always.
 - 'heating' alone does NOT trigger the weather tool — requires meteorological keywords.
"""

import logging
import re
from typing import Dict, Any, Optional

from src.tools.weather_tool import weather_tool, WeatherTool
from src.tools.meter_tool import meter_tool, MeterTool
from src.tools.tariff_tool import tariff_tool, TariffTool
from src.tools.rag_tool import rag_tool, RAGTool

logger = logging.getLogger("ecopulse.agent")

# ─────────────────────────────────────────────────────────────────────────────
# INTENT DETECTION PATTERNS  (ordered from most specific → least specific)
# ─────────────────────────────────────────────────────────────────────────────

# "Calculation" patterns — user wants an arithmetic answer (energy/cost math)
_CALC_PATTERNS = [
    r"\bhow\s+much\s+(energy|power|electricity|kwh|watt)\b",
    r"\b(calculate|compute|work\s+out|estimate)\s+(energy|power|electricity|watt|kwh|cost)\b",
    r"\b(watt|kilowatt|kw|kwh)\s+(consumed|used|drawn|needed|required)\b",
    r"\b(energy|power)\s+consumed?\s+by\b",
    r"\b\d+\s*(watt|kw|kwh|celsius|celsius|degree)\b",
    r"\bhow\s+long\s+(to|will)\s+(charge|heat|cool|run)\b",
]

# Meter analysis — needs a MAC household ID or explicit meter vocabulary
_METER_PATTERNS = [
    r"\b(MAC\d{6})\b",
    r"\b(meter|smart\s+meter|smart meter|half.hourly|half\s+hourly|diurnal)\b",
    r"\b(vampire\s+load|baseline\s+draw|overnight\s+draw|standby\s+draw)\b",
    r"\b(consumption|usage)\s+(data|history|report|pattern|trend)\b",
    r"\b(analyze|analyse|diagnose)\s+.*(household|home|meter|mac)\b",
    r"\b(anomaly|spike)\s+(in|on|for)\b",
]

# Weather — must have explicit meteorological / forecast words (NOT just "heating")
_WEATHER_PATTERNS = [
    r"\b(weather|forecast|climate|meteorol)\b",
    r"\b(tomorrow|this\s+week|rain|wind|cloud|sunny|overcast|storm)\b",
    r"\b(temperature\s+tomorrow|degrees?\s+tomorrow|how\s+cold|how\s+hot)\b",
    r"\b(heating\s+demand|cooling\s+demand)\s+(forecast|prediction|estimate)\b",
    r"\b(outdoor\s+temperature|ambient\s+temperature)\b",
]

# Tariff / scheduling — must reference ToU, EV, appliance runtime, or cost optimisation
_TARIFF_PATTERNS = [
    r"\b(tariff|tou|time.of.use|off.peak|peak\s+rate|cheap\s+rate)\b",
    r"\b(when\s+(should|to|is\s+it\s+best)\s+(i|to)\s+(run|charge|use|start))\b",
    r"\b(ev\s+charger?|electric\s+vehicle\s+charg|car\s+charger?)\b",
    r"\b(best\s+time\s+to|cheapest\s+time|lowest\s+rate|avoid\s+peak)\b",
    r"\b(schedule\s+(washing|dishwasher|dryer|heater|pump))\b",
    r"\b(bill\s+shock|monthly\s+bill|electricity\s+bill\s+(too\s+high|spike))\b",
]

# Conservation advice — generic efficiency, tips, retrofits
_CONSERVATION_PATTERNS = [
    r"\b(save|saving|conserve|reduce|efficient|efficiency)\b",
    r"\b(tip|advice|recommend|improve|lower|cut)\s+.*(energy|electricity|bill|consumption)\b",
    r"\b(led|cfl|bulb|tube\s+light|fluorescent)\b",
    r"\b(air\s+conditioner|air\s+conditioning|thermostat|hvac)\b",
    r"\b(refrigerator|fridge|freezer|door\s+seal)\b",
    r"\b(water\s+heater|geyser|immersion|boiler)\b",
    r"\b(standby|phantom\s+load|sleep\s+mode|charger\s+left\s+in)\b",
    r"\b(insulate|insulation|draught|draft|window\s+seal)\b",
]

# ── RAG category keyword map (appliance → vector-store category)
_RAG_CATEGORY_MAP = [
    (r"\b(bulb|cfl|led|tube\s+light|fluorescent|incandescent|lumen)\b", "lighting"),
    (r"\b(air\s+conditioner|ac\b|hvac|thermostat|fan|cooling|air\s+con)\b", "hvac"),
    (r"\b(refrigerator|fridge|freezer|compressor|door\s+seal|defrost)\b", "refrigeration"),
    (r"\b(water\s+heater|geyser|immersion|hot\s+water|boiler)\b", "water_heater"),
    (r"\b(standby|phantom|sleep\s+mode|charger|monitor|computer|pc)\b", "standby"),
    (r"\b(microwave|kettle|oven|cooking|hob|stove)\b", "appliances"),
    (r"\b(circuit|555\s+timer|ldr|lm35|sensor|relay|monostable)\b", "circuit_design"),
]

# ── Appliance power defaults (Watts) for energy calculation
_APPLIANCE_POWER_W = {
    "microwave": 1000, "oven": 2400, "kettle": 2000, "toaster": 1000,
    "washing machine": 2200, "dryer": 3000, "dishwasher": 1500,
    "fridge": 150, "freezer": 200, "refrigerator": 150,
    "air conditioner": 1500, "ac": 1500, "heat pump": 3500,
    "electric heater": 2000, "fan heater": 2000, "oil heater": 2000,
    "tv": 100, "led tv": 80, "monitor": 50, "computer": 200, "laptop": 50,
    "hair dryer": 1800, "iron": 2200, "vacuum": 1200,
    "ev charger": 7200, "water heater": 3000, "geyser": 3000,
    "led bulb": 9, "cfl": 15, "incandescent bulb": 60, "tube light": 40,
    "fan": 75, "ceiling fan": 75,
}

DOMAIN_CONSTANTS = {
    "cfl_savings_pct": 75,
    "ac_savings_per_degree_pct": "3-5",
    "ac_recommended_setpoint_c": 25,
    "water_heater_savings_60_to_50_pct": 18,
    "dirty_bulb_lumen_loss_pct": 50,
    "sleep_mode_savings_pct": 40,
    "shading_ac_reduction_pct": 40,
    "ceiling_fan_cost_paise_per_hr": 30,
    "ac_cost_rupees_per_hr": 10,
    "grid_transmission_loss_pct": 16,
    "cfl_annual_savings_rupees": 700,
    "incandescent_heat_waste_pct": 90
}


class EcoPulseAgent:
    """
    EcoPulse AI Core Agent — v2 (Precise intent detection, targeted tool dispatch,
    direct calculation engine, strict RAG category matching).
    """

    def __init__(self):
        self.weather: WeatherTool = weather_tool
        self.meter: MeterTool = meter_tool
        self.tariff: TariffTool = tariff_tool
        self.rag: RAGTool = rag_tool

    # ──────────────────────────────────────────────────────────────────────────
    # EXTRACTION HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def _extract_household_id(self, text: str) -> Optional[str]:
        m = re.search(r'\bMAC\d{6}\b', text, re.IGNORECASE)
        return m.group(0).upper() if m else None

    def _extract_dates(self, text: str):
        dates = re.findall(r'\b(\d{4}-\d{2}-\d{2})\b', text)
        if len(dates) >= 2:
            return dates[0], dates[1]
        elif len(dates) == 1:
            return dates[0], dates[0]
        return "2013-01-01", "2013-01-14"

    def _extract_appliance_type(self, text: str) -> str:
        t = text.lower()
        if re.search(r'\bev\b|electric\s+vehicle|car\s+charger', t): return "ev_charger"
        if re.search(r'\bheat\s+pump\b', t):                          return "heat_pump"
        if re.search(r'\bwashing\b|\bdryer\b|\blaundry\b', t):        return "washing_machine"
        if re.search(r'\bdishwasher\b', t):                           return "dishwasher"
        if re.search(r'\bwater\s+heater\b|\bimmersion\b|\bgeyser\b', t): return "water_heater"
        return "general"

    def _match_patterns(self, text: str, patterns: list) -> bool:
        t = text.lower()
        return any(re.search(p, t) for p in patterns)

    def _resolve_rag_category(self, text: str) -> str:
        t = text.lower()
        for pattern, cat in _RAG_CATEGORY_MAP:
            if re.search(pattern, t):
                return cat
        return "all"

    # ──────────────────────────────────────────────────────────────────────────
    # ENERGY CALCULATION ENGINE
    # ──────────────────────────────────────────────────────────────────────────

    def _extract_power_watts(self, text: str) -> Optional[float]:
        """Extracts wattage from text: '1300 watt', '1.3 kW', '130 celsius' is not wattage."""
        # Direct watt mention
        m = re.search(r'(\d+(?:\.\d+)?)\s*(?:watt|w)\b', text, re.IGNORECASE)
        if m:
            return float(m.group(1))
        # kW mention
        m = re.search(r'(\d+(?:\.\d+)?)\s*kw\b', text, re.IGNORECASE)
        if m:
            return float(m.group(1)) * 1000
        # Named appliance match
        text_lower = text.lower()
        for name, watts in _APPLIANCE_POWER_W.items():
            if name in text_lower:
                return float(watts)
        return None

    def _extract_time_hours(self, text: str) -> Optional[float]:
        """Extracts duration from text: '15 min', '15 minutes', '2 hours', '30 seconds'."""
        t_lower = text.lower()
        if "half an hour" in t_lower or "half hour" in t_lower:
            return 0.5
        if "quarter of an hour" in t_lower or "quarter hour" in t_lower:
            return 0.25

        # Minutes: minutes, minute, mins, min
        m = re.search(r'(\d+(?:\.\d+)?)\s*(?:minutes?|mins?)\b', text, re.IGNORECASE)
        if m:
            return float(m.group(1)) / 60.0
        # Hours: hours, hour, hrs, hr
        m = re.search(r'(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)\b', text, re.IGNORECASE)
        if m:
            return float(m.group(1))
        # Seconds: seconds, second, secs, sec
        m = re.search(r'(\d+(?:\.\d+)?)\s*(?:seconds?|secs?)\b', text, re.IGNORECASE)
        if m:
            return float(m.group(1)) / 3600.0
        return None

    def _compute_energy_answer(self, message: str) -> Optional[str]:
        """
        Attempts direct energy/cost calculation from user message.
        Returns a formatted answer string, or None if insufficient data.
        """
        power_w = self._extract_power_watts(message)
        time_h  = self._extract_time_hours(message)

        if power_w is None and time_h is None:
            return None

        # If we have at least one value, attempt a response
        lines = ["\n## ⚡ Energy Calculation Result\n"]

        if power_w is not None and time_h is not None:
            energy_kwh = (power_w * time_h) / 1000.0
            cost_flat  = round(energy_kwh * 0.18, 4)   # UK flat rate
            cost_off   = round(energy_kwh * 0.08, 4)   # Off-peak
            cost_peak  = round(energy_kwh * 0.38, 4)   # Peak surge

            lines += [
                "**Formula:** `E (kWh) = (Power in Watts × Time in Hours) / 1000`",
                f"**Calculation:** `({power_w:.0f} W × {time_h:.3f} hrs) / 1000` = **`{energy_kwh:.4f} kWh`**\n",
                "| Parameter | Value |",
                "|-----------|-------|",
                f"| **Appliance Power** | **{power_w:.0f} W** ({power_w/1000:.2f} kW) |",
                f"| **Run Duration** | **{time_h*60:.1f} minutes** ({time_h:.3f} hours) |",
                f"| **Energy Consumed** | **{energy_kwh:.4f} kWh** ({energy_kwh*1000:.2f} Wh) |",
                f"| Cost (Flat rate £0.18/kWh) | £{cost_flat:.4f} |",
                f"| Cost (Off-peak £0.08/kWh) | £{cost_off:.4f} ✅ |",
                f"| Cost (Peak surge £0.38/kWh) | £{cost_peak:.4f} 🔴 |\n",
            ]

            # Contextual tips
            if power_w >= 800 and "microwave" in message.lower():
                lines.append("> 💡 **Efficiency Tip:** Microwaves can save up to **50% on cooking energy costs** compared to a conventional oven for small quantities of food. Cook from the outside edge inward for optimal heat distribution. [Source: energy.txt]")
            elif power_w >= 2000:
                lines.append(f"> 💡 **Tip:** This is a high-power load ({power_w:.0f} W). Run it during **off-peak hours (01:00–07:00)** on a ToU tariff to minimise cost to £{cost_off:.4f} instead of £{cost_peak:.4f} at peak rates.")
            elif "kettle" in message.lower():
                lines.append("> 💡 **Tip:** Only boil the amount of water you need — overfilling wastes energy. A dirty kettle takes more energy to heat; descale regularly with vinegar and water. [Source: energy.txt]")

        elif power_w is not None:
            # Only power known
            lines += [
                f"| Appliance Power | {power_w:.0f} W ({power_w/1000:.2f} kW) |",
                "",
                "**To calculate energy consumed:**",
                f"`E (kWh) = ({power_w:.0f} W × Duration in Hours) / 1000`",
                "",
                "Please also provide the **run duration** (e.g. '15 minutes', '2 hours') to get the exact kWh figure."
            ]
        elif time_h is not None:
            # Only time known
            lines += [
                f"| Run Duration | {time_h*60:.1f} minutes |",
                "",
                "Please also specify the **appliance name or power rating** (in watts or kW) to calculate energy consumption."
            ]

        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────────────
    # RESPONSE FORMATTERS
    # ──────────────────────────────────────────────────────────────────────────

    def _format_meter_response(self, result: Dict[str, Any]) -> str:
        if result.get("status") == "error":
            return f"\n## ⚠️ Meter Lookup Error\n{result['message']}\n"
        if result.get("status") == "warning":
            return f"\n## ⚠️ No Readings Found\n{result['message']}\n"

        hh = result["household"]
        metrics = result["summary_metrics"]
        cohort = result["cohort_benchmark"]
        anomalies = result.get("anomalies_detected", [])
        period = result.get("period", {})

        standing_emoji = {
            "ABOVE_AVERAGE_CONSUMER": "⬆️",
            "BELOW_AVERAGE_EFFICIENT": "⬇️✅",
            "ON_PAR_WITH_COHORT": "🟰"
        }.get(cohort["relative_standing"], "🟰")

        parts = [
            f"\n## ⚡ Smart Meter Analysis: `{hh['household_id']}`",
            f"**Tariff:** `{hh['tariff_type']}` | **ACORN Group:** `{hh['acorn_group']}` (`{hh['acorn_code']}`)",
            f"**Period:** {period.get('start_date','?')} → {period.get('end_date','?')} ({period.get('days_analyzed','?')} days)\n",
            "### 📊 Consumption Summary",
            "| Metric | Value |",
            "|--------|-------|",
            f"| **Total Consumption** | **{metrics['total_consumption_kwh']} kWh** |",
            f"| Daily Mean | {metrics['mean_daily_kwh']} kWh |",
            f"| Daily Median | {metrics['median_daily_kwh']} kWh |",
            f"| Peak Day | {metrics['max_daily_kwh']} kWh |",
            f"| Lowest Day | {metrics['min_daily_kwh']} kWh |",
            f"| Overnight Vampire Draw | {metrics['overnight_baseline_kwh']} kWh/slot |",
            f"| Evening Peak Draw | {metrics['evening_peak_kwh']} kWh/slot |\n",
            f"### 👥 ACORN `{cohort['cohort_name']}` Cohort Benchmark",
            f"- **Cohort Average:** {cohort['cohort_mean_kwh']} kWh/day",
            f"- **Your Average:** {metrics['mean_daily_kwh']} kWh/day  ({'+' if cohort['household_vs_cohort_diff_pct'] > 0 else ''}{cohort['household_vs_cohort_diff_pct']}%)",
            f"- **Standing:** {standing_emoji} `{cohort['relative_standing'].replace('_', ' ')}`\n",
        ]

        if anomalies:
            parts.append(f"### 🚨 Anomalies Detected ({len(anomalies)} alerts)")
            for a in anomalies[:4]:
                sev_emoji = "🔴" if a["severity"] in ["HIGH", "CRITICAL"] else "🟡"
                parts.append(
                    f"{sev_emoji} **{a['date']}** — `{a['type']}` ({a['severity']})  \n"
                    f"  → Observed: **{a['observed_kwh']} kWh** | Expected: ~{a['expected_kwh']} kWh  \n"
                    f"  → {a['diagnosis']}"
                )
            parts.append("")
        else:
            parts.append("### ✅ No Anomalies Detected\nConsumption pattern is within normal statistical bounds for your cohort.\n")

        return "\n".join(parts)

    def _format_weather_response(self, result: Dict[str, Any]) -> str:
        if result.get("status") != "success":
            return "\n## ⚠️ Weather data unavailable.\n"
        s = result["summary"]
        stress_emoji = {
            "HIGH_HEATING_DEMAND_FREEZE_RISK": "🥶❄️",
            "MODERATE_HEATING_DEMAND":         "🌥️🧣",
            "HIGH_COOLING_DEMAND":             "🌡️🔥",
            "BALANCED_COMFORT_ZONE":           "🌤️✅"
        }.get(s["thermal_stress_index"], "🌤️")

        lines = [
            "\n## 🌤️ Weather & Thermal Demand Analysis",
            f"**Location:** {result['location']['city']}\n",
            "| Parameter | Value |",
            "|-----------|-------|",
            f"| Average Temperature | **{s['average_temperature_c']}°C** |",
            f"| Feels-Like | **{s['average_feels_like_c']}°C** |",
            f"| Min / Max | {s['min_temperature_c']}°C / {s['max_temperature_c']}°C |",
            f"| Heating Degree Days (HDD) | **{s['heating_degree_days_hdd']}** |",
            f"| Cooling Degree Days (CDD) | {s['cooling_degree_days_cdd']} |\n",
            f"**Thermal Stress:** {stress_emoji} `{s['thermal_stress_index'].replace('_', ' ')}`",
            f"\n> 💡 **Energy Advisory:** {s['energy_advisory']}\n",
        ]
        if s["heating_degree_days_hdd"] > 5:
            lines += [
                "**⚡ Energy Impact:**",
                "- Each 1°C rise in thermostat setpoint adds **3–5% energy cost**. [Source: energy.txt]",
                "- Shading windows cuts A/C draw by up to **40%**. [Source: energy.txt]",
                "- Ceiling fans cost **~30 paise/hr** vs. air conditioners at **~Rs. 10.00/hr**. [Source: energy.txt]\n"
            ]
        return "\n".join(lines)

    def _format_tariff_response(self, result: Dict[str, Any]) -> str:
        if result.get("status") != "success":
            return "\n## ⚠️ Tariff calculation error.\n"
        app   = result["appliance"]
        costs = result["cost_breakdown"]
        sched = result["schedule"]
        lines = [
            f"\n## 💰 Tariff Optimiser: {app['name']}",
            f"**Load:** {app['power_draw_kw']} kW × {app['duration_hours']} hrs = **{app['total_energy_kwh']} kWh** per cycle\n",
            "### 📊 Cost Comparison",
            "| Window | Time | Rate | Cost | Status |",
            "|--------|------|------|------|--------|",
            f"| Peak Surge | {sched['restricted_window']['time_range']} | £{result['tariff_context']['tou_rates']['peak_surge']:.2f}/kWh | **{sched['restricted_window']['total_run_cost']}** | 🔴 Avoid |",
            f"| Standard   | {sched['alternative_window']['time_range']} | £{result['tariff_context']['tou_rates']['standard']:.2f}/kWh | {sched['alternative_window']['total_run_cost']} | 🟡 OK |",
            f"| Off-Peak   | {sched['optimal_window']['time_range']}   | £{result['tariff_context']['tou_rates']['off_peak']:.2f}/kWh | **{sched['optimal_window']['total_run_cost']}** | ✅ Best |\n",
            f"**Saving per cycle:** £{costs['single_cycle_savings_gbp']:.2f} ({costs['savings_percentage']}% reduction)",
            f"**Annual savings (156 cycles):** 💰 **£{costs['annualized_projected_savings_gbp']:.2f}/year**\n",
            f"> {result['actionable_advice']}\n"
        ]
        return "\n".join(lines)

    def _format_rag_response(self, result: Dict[str, Any], min_score: float = 0.15) -> str:
        if result.get("status") == "empty" or not result.get("chunks"):
            return ""
        # Filter chunks by minimum relevance score to prevent off-topic RAG hallucinations
        valid_chunks = [c for c in result["chunks"] if c.get("relevance_score", 0) >= min_score]
        if not valid_chunks:
            return ""
        lines = ["\n## 📚 Verified Conservation Guidelines"]
        for chunk in valid_chunks[:2]:          # max 2 chunks
            lines.append(f"\n**{chunk['title']}** *(Category: {chunk['category']})*")
            lines.append(f"> {chunk['content']}")
            lines.append(f"*[Source: {chunk['reference']}]*")
        lines.append("")
        return "\n".join(lines)

    def _classify_intent(self, text: str) -> Dict[str, bool]:
        msg = text.strip()
        return {
            "calculation": self._match_patterns(msg, _CALC_PATTERNS),
            "meter_analysis": self._match_patterns(msg, _METER_PATTERNS) or bool(self._extract_household_id(msg)),
            "weather": self._match_patterns(msg, _WEATHER_PATTERNS),
            "tariff": self._match_patterns(msg, _TARIFF_PATTERNS),
            "conservation": self._match_patterns(msg, _CONSERVATION_PATTERNS)
        }

    # ──────────────────────────────────────────────────────────────────────────
    # MAIN PROCESS METHOD
    # ──────────────────────────────────────────────────────────────────────────

    def process(self, message: str, household_id: Optional[str] = None) -> str:
        """
        Single entry point. Classifies intent precisely, dispatches only the
        required tools, and synthesises a focused, accurate response.
        """
        msg = message.strip()

        intents = self._classify_intent(msg)
        is_calculation  = intents["calculation"]
        is_meter        = intents["meter_analysis"]
        is_weather      = intents["weather"]
        is_tariff       = intents["tariff"]
        is_conservation = intents["conservation"]

        # Household extraction
        extracted_hh   = self._extract_household_id(msg) or household_id
        start_date, end_date = self._extract_dates(msg)
        appliance      = self._extract_appliance_type(msg)

        tool_results   = {}
        sections       = ["# ⚡ EcoPulse AI Response\n"]

        # ── PRIORITY 1: Direct energy math calculation
        if is_calculation:
            calc_block = self._compute_energy_answer(msg)
            if calc_block:
                sections.append(calc_block)
                # Still add a targeted RAG tip if appliance-specific
                rag_cat = self._resolve_rag_category(msg)
                if rag_cat != "all":
                    try:
                        rag_result = self.rag.retrieve_energy_knowledge(query=msg, category=rag_cat, top_k=1)
                        rag_block = self._format_rag_response(rag_result, min_score=0.10)
                        if rag_block:
                            sections.append(rag_block)
                    except Exception as e:
                        logger.error(f"RAG error in calc path: {e}")
                return "\n".join(sections)

        # ── PRIORITY 2: Smart Meter Analysis (requires household ID)
        if is_meter and extracted_hh:
            try:
                meter_result = self.meter.analyze_smart_meter_consumption(
                    household_id=extracted_hh,
                    start_date=start_date,
                    end_date=end_date,
                    granularity="half_hourly",
                    detect_anomalies=True
                )
                sections.append(self._format_meter_response(meter_result))
                tool_results["meter"] = meter_result
            except Exception as e:
                logger.error(f"Meter tool error: {e}")

        # ── PRIORITY 3: Weather Forecast (ONLY when explicitly about weather/climate)
        if is_weather:
            try:
                weather_result = self.weather.get_weather_forecast(
                    latitude=51.5074, longitude=-0.1278,
                    forecast_type="hourly", target_date=start_date
                )
                sections.append(self._format_weather_response(weather_result))
                tool_results["weather"] = weather_result
            except Exception as e:
                logger.error(f"Weather tool error: {e}")

        # ── PRIORITY 4: Tariff Scheduler (ONLY when explicitly about costs/scheduling/EV)
        if is_tariff:
            try:
                tariff_result = self.tariff.calculate_tariff_cost_and_schedule(
                    household_id=extracted_hh,
                    appliance_type=appliance,
                    target_date=start_date
                )
                sections.append(self._format_tariff_response(tariff_result))
                tool_results["tariff"] = tariff_result
            except Exception as e:
                logger.error(f"Tariff tool error: {e}")

        # ── PRIORITY 5: Conservation advice (RAG — tightly category-matched)
        is_energy_domain = any([
            is_calculation, is_meter, is_weather, is_tariff, is_conservation,
            self._resolve_rag_category(msg) != "all",
            self._match_patterns(msg, [
                r"\b(energy|power|electricity|kwh|watt|kw|voltage|bill|tariff|meter|appliance|lighting|bulb|cfl|led|hvac|ac|thermostat|heating|cooling|refrigerator|fridge|freezer|geyser|boiler|standby|vampire|solar|circuit|555|ldr|lm35|relay|mac\d{6})\b"
            ])
        ])

        if is_conservation or (not tool_results and not is_calculation and is_energy_domain):
            rag_cat = self._resolve_rag_category(msg)
            min_score = 0.12 if is_conservation or rag_cat != "all" else 0.20
            try:
                rag_result = self.rag.retrieve_energy_knowledge(
                    query=msg,
                    category=rag_cat,
                    top_k=2  # Focused: 2 chunks max
                )
                rag_block = self._format_rag_response(rag_result, min_score=min_score)
                if rag_block:
                    sections.append(rag_block)
            except Exception as e:
                logger.error(f"RAG tool error: {e}")

        # ── Append action items ONLY when meter/weather/tariff results exist (not for every query)
        if tool_results:
            sections.append(self._generate_action_items(tool_results))

        # ── Out of domain / Fallback: if nothing matched, return a clear domain boundary message
        if len(sections) == 1:
            sections.append(
                "\n## ⚠️ Out of Domain Query\n\n"
                "I cannot answer this question as it is outside my domain of expertise.\n\n"
                "I am **EcoPulse AI**, an energy intelligence assistant specialized in smart meter consumption analytics, thermal weather demand, ToU tariff optimization, and energy conservation advice.\n\n"
                "### 💬 How I Can Help You:\n"
                "- **⚡ Energy Math**: *'How much energy does a 1000W microwave use in 15 minutes?'*\n"
                "- **📊 Meter Diagnostics**: *'Analyze household MAC000002 from 2013-01-01 to 2013-01-14'*\n"
                "- **🌤️ Weather & Thermal Demand**: *'What's the weather forecast and heating impact?'*\n"
                "- **💰 Tariff Optimization**: *'When should I run my EV charger or washing machine?'*\n"
                "- **💡 Conservation Advice**: *'How do I reduce my refrigerator energy use?'*\n"
            )

        return "\n".join(sections)

    def _generate_action_items(self, tool_results: Dict) -> str:
        """Generates contextual action items ONLY based on actual tool results."""
        lines = ["---\n## ✅ Immediate Action Items\n"]
        priority = 1

        if "meter" in tool_results:
            anomalies = tool_results["meter"].get("anomalies_detected", [])
            if anomalies:
                lines.append(f"**{priority}. 🔴 Address Detected Anomalies**")
                lines.append("   - Run the *flashlight door seal test* on your refrigerator (shine torch inside, close door, look for light leaks). [Source: energy.txt]")
                lines.append("   - Unplug wall chargers and enable sleep-mode on computers — saves ~**40%** on standby power. [Source: energy.txt]")
                priority += 1

        if "weather" in tool_results:
            hdd = tool_results["weather"].get("summary", {}).get("heating_degree_days_hdd", 0)
            if hdd > 3:
                lines.append(f"**{priority}. 🌡️ Weather-Smart Heating**")
                lines.append("   - Pre-heat rooms 07:00–15:00 before cold evening peak rates kick in.")
                lines.append("   - Raising AC above 22°C → **3–5% energy saved per degree** (optimal: **25°C**). [Source: energy.txt]")
                priority += 1

        if "tariff" in tool_results:
            savings = tool_results["tariff"].get("cost_breakdown", {})
            lines.append(f"**{priority}. 💰 Activate Load Shifting**")
            lines.append("   - Run all heavy appliances between **01:00–07:00** (off-peak window).")
            lines.append(f"   - Annual saving potential: £**{savings.get('annualized_projected_savings_gbp', 0):.2f}** (156 cycles/year).")
            priority += 1

        return "\n".join(lines)


# Global singleton
agent = EcoPulseAgent()
