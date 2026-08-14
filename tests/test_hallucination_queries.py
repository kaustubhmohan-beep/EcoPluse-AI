import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agent import EcoPulseAgent


def _process(query: str) -> str:
    return EcoPulseAgent().process(query)


def test_heating_bill_does_not_trigger_weather():
    q = "My heating bill is high and I want to save money"
    resp = _process(q)

    assert "Weather & Thermal Demand Analysis" not in resp
    assert "EcoPulse AI Response" in resp or "General Knowledge & Context" in resp or "Verified Conservation Guidelines" in resp
    assert "heating" in resp.lower() or "energy" in resp.lower() or "bill" in resp.lower() or "save" in resp.lower()


def test_explicit_weather_query_still_uses_weather_tool():
    q = "What is the weather forecast in London tomorrow?"
    resp = _process(q)

    assert "Weather & Thermal Demand Analysis" in resp
    assert "London" in resp or "Location" in resp


def test_vague_bill_question_does_not_trigger_tariff():
    q = "I need advice on my electricity bill and how to reduce it"
    resp = _process(q)

    assert "Tariff Optimiser" not in resp
    assert "Verified Conservation Guidelines" in resp or "EcoPulse AI Response" in resp


def test_explicit_ev_charging_question_triggers_tariff():
    q = "When is the cheapest time to charge my EV?"
    resp = _process(q)

    assert "Tariff Optimiser" in resp
    assert "EV" in resp or "charge" in resp.lower() or "off-peak" in resp.lower()


def test_out_of_context_query_stays_out_of_energy_domain():
    q = "Who is the prime minister of India?"
    resp = _process(q)

    assert "General Knowledge & Context" in resp
    assert "Narendra Modi" in resp
    assert "Weather & Thermal Demand Analysis" not in resp
    assert "Tariff Optimiser" not in resp


def test_energy_conservation_query_stays_in_energy_domain():
    q = "How can I save energy on my lighting and reduce my electricity bill?"
    resp = _process(q)

    assert "General Knowledge & Context" not in resp
    assert "Verified Conservation Guidelines" in resp or "Energy Calculation Result" in resp or "EcoPulse AI Response" in resp
    assert "lighting" in resp.lower() or "energy" in resp.lower() or "CFL" in resp or "LED" in resp or "bulb" in resp.lower()
