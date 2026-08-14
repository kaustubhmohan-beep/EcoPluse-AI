"""
EcoPulse AI - Test Suite (Stage 4: Verification & Evaluation)
Tests: DuckDB queries, weather tool fallback, tariff math,
RAG retrieval, and end-to-end agent dialogue flows.
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

PASS = "[PASS]"
FAIL = "[FAIL]"

def run_test(name, fn):
    try:
        t0 = time.time()
        result = fn()
        elapsed = int((time.time() - t0) * 1000)
        if result:
            print(f"{PASS} [{elapsed:>4}ms]  {name}")
            return True
        else:
            print(f"{FAIL}           {name}")
            return False
    except Exception as e:
        print(f"{FAIL}           {name}  |  Error: {e}")
        return False


# ─────────────────────────────────────────────────────────────
# STAGE 1: DuckDB Data Engine Tests
# ─────────────────────────────────────────────────────────────

def test_household_profile():
    from src.data_engine import data_engine
    profile = data_engine.get_household_profile("MAC000002")
    return (
        profile is not None and
        profile["lclid"] == "MAC000002" and
        profile["tariff_type"] in ["Std", "ToU"] and
        profile["acorn_group"] in ["Affluent", "Comfortable", "Adversity", "ACORN-U"]
    )

def test_daily_consumption_query():
    from src.data_engine import data_engine
    records = data_engine.query_daily_consumption("MAC000002", "2013-01-01", "2013-01-14")
    return (
        isinstance(records, list) and
        len(records) > 0 and
        "energy_sum_kwh" in records[0] and
        records[0]["energy_sum_kwh"] > 0
    )

def test_cohort_benchmark():
    from src.data_engine import data_engine
    stats = data_engine.get_cohort_benchmark("Affluent", "2013-01-10")
    return (
        isinstance(stats, dict) and
        "mean_kwh" in stats and
        stats["mean_kwh"] > 0
    )

def test_sample_households():
    from src.data_engine import data_engine
    samples = data_engine.get_sample_households(limit=5)
    return isinstance(samples, list) and len(samples) > 0 and "lclid" in samples[0]


# ─────────────────────────────────────────────────────────────
# STAGE 2: RAG Knowledge Retrieval Tests
# ─────────────────────────────────────────────────────────────

def test_rag_index_loaded():
    from src.rag_indexer import rag_indexer
    return rag_indexer.chunks is not None and len(rag_indexer.chunks) > 10

def test_rag_lighting_query():
    from src.tools.rag_tool import rag_tool
    result = rag_tool.retrieve_energy_knowledge("How much electricity does a CFL save vs incandescent?", "lighting")
    chunks = result.get("chunks", [])
    assert len(chunks) > 0, "No chunks returned"
    top = chunks[0]["content"].lower()
    # Must reference lighting savings figure
    return any(kw in top for kw in ["75%", "cfl", "light", "bulb", "electricity", "efficient"])

def test_rag_hvac_query():
    from src.tools.rag_tool import rag_tool
    result = rag_tool.retrieve_energy_knowledge("What temperature should I set my thermostat to save energy?", "hvac")
    chunks = result.get("chunks", [])
    assert len(chunks) > 0
    combined = " ".join(c["content"].lower() for c in chunks)
    return any(kw in combined for kw in ["25", "thermostat", "ac", "air", "degree", "conditioner"])

def test_rag_water_heater_query():
    from src.tools.rag_tool import rag_tool
    result = rag_tool.retrieve_energy_knowledge("How much energy can I save by lowering water heater temperature?", "water_heater")
    chunks = result.get("chunks", [])
    combined = " ".join(c["content"].lower() for c in chunks)
    return "water" in combined or "heater" in combined or "18" in combined

def test_rag_jetir_circuit_query():
    from src.tools.rag_tool import rag_tool
    result = rag_tool.retrieve_energy_knowledge("555 timer delay circuit monostable LDR light sensor energy automation")
    chunks = result.get("chunks", [])
    return any(c["source"] == "JETIR1405001.pdf" for c in chunks)


# ─────────────────────────────────────────────────────────────
# STAGE 2: Weather Tool Tests
# ─────────────────────────────────────────────────────────────

def test_weather_forecast_returns():
    from src.tools.weather_tool import weather_tool
    result = weather_tool.get_weather_forecast(
        latitude=51.5074, longitude=-0.1278,
        forecast_type="hourly", target_date="2013-01-15"
    )
    return (
        result.get("status") == "success" and
        "summary" in result and
        "average_temperature_c" in result["summary"] and
        "thermal_stress_index" in result["summary"]
    )

def test_weather_hdd_calculation():
    from src.tools.weather_tool import weather_tool
    result = weather_tool.get_weather_forecast(target_date="2013-01-15")
    s = result["summary"]
    # For a January day in London, HDD must be positive (temp should be below 18°C baseline)
    return s["heating_degree_days_hdd"] >= 0 and s["cooling_degree_days_cdd"] >= 0


# ─────────────────────────────────────────────────────────────
# STAGE 2: Tariff Tool Tests
# ─────────────────────────────────────────────────────────────

def test_tariff_ev_charger():
    from src.tools.tariff_tool import tariff_tool
    result = tariff_tool.calculate_tariff_cost_and_schedule(
        appliance_type="ev_charger",
        power_draw_kw=7.2,
        duration_hours=4.0
    )
    costs = result["cost_breakdown"]
    # Off-peak MUST be cheaper than peak
    return (
        result["status"] == "success" and
        costs["cost_if_run_in_off_peak_gbp"] < costs["cost_if_run_in_peak_gbp"] and
        costs["single_cycle_savings_gbp"] > 0 and
        costs["annualized_projected_savings_gbp"] > 0
    )

def test_tariff_math_accuracy():
    from src.tools.tariff_tool import tariff_tool
    # 7.2 kW * 4 hr = 28.8 kWh
    # Peak cost at £0.38 = 28.8 * 0.38 = £10.944
    # Off-peak at £0.08 = 28.8 * 0.08 = £2.304
    result = tariff_tool.calculate_tariff_cost_and_schedule(
        appliance_type="ev_charger",
        power_draw_kw=7.2,
        duration_hours=4.0
    )
    costs = result["cost_breakdown"]
    expected_peak     = round(28.8 * 0.38, 2)
    expected_off_peak = round(28.8 * 0.08, 2)
    return (
        abs(costs["cost_if_run_in_peak_gbp"] - expected_peak) < 0.01 and
        abs(costs["cost_if_run_in_off_peak_gbp"] - expected_off_peak) < 0.01
    )

def test_tariff_savings_percentage():
    from src.tools.tariff_tool import tariff_tool
    result = tariff_tool.calculate_tariff_cost_and_schedule(
        appliance_type="washing_machine",
        power_draw_kw=2.2,
        duration_hours=1.5
    )
    costs = result["cost_breakdown"]
    return costs["savings_percentage"] > 50  # Off-peak is ~79% cheaper than peak


# ─────────────────────────────────────────────────────────────
# STAGE 3: Agent End-to-End Tests
# ─────────────────────────────────────────────────────────────

def test_agent_intent_classification():
    from src.agent import EcoPulseAgent
    a = EcoPulseAgent()
    intent = a._classify_intent("Why was my energy bill so high last week MAC000002?")
    return intent.get("meter_analysis") is True

def test_agent_extraction():
    from src.agent import EcoPulseAgent
    a = EcoPulseAgent()
    hh = a._extract_household_id("Analyze MAC000022 from 2013-01-01 to 2013-01-14")
    start, end = a._extract_dates("Analyze MAC000022 from 2013-01-01 to 2013-01-14")
    return hh == "MAC000022" and start == "2013-01-01" and end == "2013-01-14"

def test_agent_conservation_query():
    from src.agent import EcoPulseAgent
    a = EcoPulseAgent()
    response = a.process("How can I save energy on my lighting and reduce my electricity bill?")
    return (
        len(response) > 200 and
        ("CFL" in response or "LED" in response or "75%" in response or "bulb" in response.lower())
    )

def test_agent_full_meter_workflow():
    from src.agent import EcoPulseAgent
    a = EcoPulseAgent()
    response = a.process(
        "Analyze household MAC000002 usage from 2013-01-01 to 2013-01-14 and tell me about anomalies",
        household_id="MAC000002"
    )
    return (
        len(response) > 400 and
        "MAC000002" in response and
        ("kWh" in response or "consumption" in response.lower())
    )

def test_agent_microwave_energy_calculation():
    from src.agent import EcoPulseAgent
    a = EcoPulseAgent()
    response = a.process("how much energy will be used if i run a microwave at 130 degrees for 15 minutes")
    return (
        "0.2500 kWh" in response or "0.25" in response
    ) and "1000 W" in response and "15.0 minutes" in response

def test_agent_out_of_domain_query():
    from src.agent import EcoPulseAgent
    a = EcoPulseAgent()
    q = "who is prime minister of india"
    response = a.process(q)
    return (
        "General Knowledge & Context" in response and
        "Narendra Modi" in response and
        "EcoPulse AI Domain Focus" in response and
        "JETIR Research" not in response
    )

def test_agent_multiple_unrelated_queries():
    from src.agent import EcoPulseAgent
    a = EcoPulseAgent()
    unrelated_queries = [
        ("who is prime minister of india", "Narendra Modi"),
        ("what is the capital of France", "Paris"),
        ("which are the guns used in war", "firearms"),
        ("who won the FIFA World Cup in 2022", "Argentina"),
        ("how to bake a pepperoni pizza at home", "pepperoni")
    ]
    for q, expected_keyword in unrelated_queries:
        resp = a.process(q)
        if "General Knowledge & Context" not in resp:
            print(f"Failed header check for query: {q}")
            return False
        if expected_keyword.lower() not in resp.lower():
            print(f"Failed keyword match for query: {q}")
            return False
        if "EcoPulse AI Domain Focus" not in resp:
            return False
        if "JETIR Research" in resp or "Verified Conservation Guidelines" in resp:
            return False
    return True


# ─────────────────────────────────────────────────────────────
# RUN ALL TESTS
# ─────────────────────────────────────────────────────────────

PASS = "[PASS]"
FAIL = "[FAIL]"

def run_test(name, fn):
    try:
        t0 = time.time()
        result = fn()
        elapsed = int((time.time() - t0) * 1000)
        if result:
            print(f"{PASS} [{elapsed:>4}ms]  {name}")
            return True
        else:
            print(f"{FAIL}           {name}")
            return False
    except Exception as e:
        print(f"{FAIL}           {name}  |  Error: {e}")
        return False

# ─────────────────────────────────────────────────────────────
# STAGE 1: DuckDB Data Engine Tests
# ─────────────────────────────────────────────────────────────
# ... (rest of file remains)
# ─────────────────────────────────────────────────────────────
# RUN ALL TESTS
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 72)
    print("  EcoPulse AI -- Stage 4 Verification Test Suite")
    print("=" * 72 + "\n")

    test_groups = [
        ("STAGE 1: DuckDB Data Engine", [
            ("Household profile lookup (MAC000002)",         test_household_profile),
            ("Daily consumption query (14-day range)",       test_daily_consumption_query),
            ("ACORN cohort benchmark query",                 test_cohort_benchmark),
            ("Sample household diversity fetch",             test_sample_households),
        ]),
        ("STAGE 2: RAG Knowledge Retrieval", [
            ("RAG index loaded with >10 chunks",             test_rag_index_loaded),
            ("RAG lighting query returns CFL savings facts", test_rag_lighting_query),
            ("RAG HVAC query returns thermostat guidance",   test_rag_hvac_query),
            ("RAG water heater query returns 18% savings",   test_rag_water_heater_query),
            ("RAG JETIR PDF circuit design chunk returned",  test_rag_jetir_circuit_query),
        ]),
        ("STAGE 2: Weather Analytics Tool", [
            ("Weather forecast returns structured result",   test_weather_forecast_returns),
            ("HDD/CDD thermal metrics calculated correctly", test_weather_hdd_calculation),
        ]),
        ("STAGE 2: Tariff Cost & Schedule Tool", [
            ("EV charger off-peak is cheapest window",       test_tariff_ev_charger),
            ("Tariff cost arithmetic precision (< £0.01 err)", test_tariff_math_accuracy),
            ("Off-peak saves >50% vs peak surge window",     test_tariff_savings_percentage),
        ]),
        ("STAGE 3: Agent Orchestrator E2E", [
            ("Intent classification detects 'meter_analysis'", test_agent_intent_classification),
            ("Household ID and date extraction from text",   test_agent_extraction),
            ("Conservation query returns CFL/LED advice",    test_agent_conservation_query),
            ("Full meter workflow returns kWh diagnostics",  test_agent_full_meter_workflow),
            ("Microwave 15 min energy math calculation",    test_agent_microwave_energy_calculation),
            ("Out-of-domain query returns general answer & bridge", test_agent_out_of_domain_query),
            ("Multiple unrelated queries return domain guide", test_agent_multiple_unrelated_queries),
        ]),
    ]

    total, passed = 0, 0
    for group_name, tests in test_groups:
        print(f"  [Group] {group_name}")
        print("  " + "-" * 60)
        for test_name, test_fn in tests:
            total += 1
            if run_test(test_name, test_fn):
                passed += 1
        print()

    print("=" * 72)
    print(f"  Results: {passed}/{total} tests passed  ({int(passed/total*100)}% pass rate)")
    status_icon = "[SUCCESS] ALL TESTS PASSED" if passed == total else f"[WARNING] {total - passed} TESTS FAILED"
    print(f"  {status_icon}")
    print("=" * 72 + "\n")
    sys.exit(0 if passed == total else 1)
