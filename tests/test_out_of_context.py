"""
EcoPulse AI - Out-of-Context Testing Suite
Verifies that EcoPulseAgent intelligently answers queries outside its primary
energy domain (e.g. world leaders, geography, sports, recipes, science, tech, math)
and bridges back to energy domain capabilities.
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agent import EcoPulseAgent

PASS = "[PASS]"
FAIL = "[FAIL]"

def run_test_query(query: str, expected_keywords: list) -> bool:
    try:
        agent = EcoPulseAgent()
        t0 = time.time()
        response = agent.process(query)
        elapsed = int((time.time() - t0) * 1000)

        # Check for core structural elements
        has_gk_header = "General Knowledge" in response
        has_domain_bridge = "EcoPulse AI Domain Focus" in response or "Energy Intelligence" in response

        # Check for expected content keywords
        resp_lower = response.lower()
        has_keywords = all(kw.lower() in resp_lower for kw in expected_keywords)

        if has_gk_header and has_domain_bridge and has_keywords:
            print(f"{PASS} [{elapsed:>4}ms] Query: '{query}'")
            return True
        else:
            print(f"{FAIL}           Query: '{query}' | Header:{has_gk_header}, Bridge:{has_domain_bridge}, Keywords:{has_keywords}")
            return False
    except Exception as e:
        print(f"{FAIL}           Query: '{query}' | Error: {e}")
        return False

def test_politics_queries():
    print("\n  [Category] Politics & World Leaders")
    print("  " + "-" * 60)
    q1 = run_test_query("who is prime minister of india", ["Narendra Modi", "India"])
    q2 = run_test_query("who is president of united states", ["Joe Biden"])
    q3 = run_test_query("who is prime minister of uk", ["Keir Starmer"])
    return q1 and q2 and q3

def test_geography_queries():
    print("\n  [Category] Geography & Capitals")
    print("  " + "-" * 60)
    q1 = run_test_query("what is the capital of France", ["Paris"])
    q2 = run_test_query("what is the capital of India", ["New Delhi"])
    q3 = run_test_query("what is the largest ocean", ["Pacific Ocean"])
    return q1 and q2 and q3

def test_sports_and_entertainment():
    print("\n  [Category] Sports & Entertainment")
    print("  " + "-" * 60)
    q1 = run_test_query("who won the FIFA World Cup in 2022", ["Argentina"])
    q2 = run_test_query("how many players in a cricket team", ["11 players"])
    q3 = run_test_query("who directed inception movie", ["Christopher Nolan"])
    return q1 and q2 and q3

def test_food_and_recipes():
    print("\n  [Category] Food & Recipes")
    print("  " + "-" * 60)
    q1 = run_test_query("how to bake a pepperoni pizza at home", ["pepperoni", "cheese", "bake"])
    q2 = run_test_query("how to prepare green tea", ["tea", "water", "steep"])
    return q1 and q2

def test_science_and_tech():
    print("\n  [Category] Science & Technology")
    print("  " + "-" * 60)
    q1 = run_test_query("what is photosynthesis", ["plants", "light", "glucose"])
    q2 = run_test_query("what is the speed of light", ["299,792,458", "meters per second"])
    q3 = run_test_query("what is Python programming language", ["programming", "interpreted"])
    return q1 and q2 and q3

def test_general_math():
    print("\n  [Category] General Math Calculations")
    print("  " + "-" * 60)
    q1 = run_test_query("what is 25 * 14", ["350"])
    q2 = run_test_query("calculate 100 / 4", ["25"])
    return q1 and q2

def test_generic_out_of_context():
    print("\n  [Category] Generic & Ambiguous Out-of-Context Queries")
    print("  " + "-" * 60)
    q1 = run_test_query("which are the guns used in war", ["firearms", "rifles"])
    q2 = run_test_query("tell me something interesting about space exploration", ["processed your query"])
    return q1 and q2

if __name__ == "__main__":
    print("\n" + "=" * 72)
    print("  EcoPulse AI -- Out-of-Context Model Training & Test Evaluation")
    print("=" * 72)

    suites = [
        test_politics_queries,
        test_geography_queries,
        test_sports_and_entertainment,
        test_food_and_recipes,
        test_science_and_tech,
        test_general_math,
        test_generic_out_of_context,
    ]

    all_passed = True
    for suite in suites:
        if not suite():
            all_passed = False

    print("\n" + "=" * 72)
    if all_passed:
        print("  [SUCCESS] ALL OUT-OF-CONTEXT TESTS PASSED SUCCESSFULLY!")
    else:
        print("  [FAILURE] SOME OUT-OF-CONTEXT TESTS FAILED.")
    print("=" * 72 + "\n")
    sys.exit(0 if all_passed else 1)
