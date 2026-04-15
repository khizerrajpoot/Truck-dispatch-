#!/usr/bin/env python3
"""
Regression test runner for HOS Trip Planner API.

Usage:
  python scripts/regression_api_tests.py
  python scripts/regression_api_tests.py --base-url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable

import requests


JSON = dict[str, Any]


@dataclass
class TestCase:
    name: str
    payload: JSON
    expected_status: int
    validator: Callable[[requests.Response], tuple[bool, str]]


def _contains_text_in_events(response_json: JSON, text: str) -> bool:
    timeline = response_json.get("timeline", [])
    for event in timeline:
        notes = str(event.get("notes", ""))
        if text.lower() in notes.lower():
            return True
    return False


def _has_core_success_shape(response_json: JSON) -> tuple[bool, str]:
    required_top = ["route", "timeline", "daily_logs", "summary"]
    missing = [key for key in required_top if key not in response_json]
    if missing:
        return False, f"Missing top-level keys: {missing}"

    if not isinstance(response_json.get("timeline"), list) or not response_json["timeline"]:
        return False, "Timeline is empty or invalid."
    if not isinstance(response_json.get("daily_logs"), list) or not response_json["daily_logs"]:
        return False, "Daily logs are empty or invalid."

    route = response_json.get("route", {})
    if route.get("total_distance_miles", 0) <= 0:
        return False, "Route total distance is not positive."
    return True, "Response shape is valid."


def validate_happy_path(resp: requests.Response) -> tuple[bool, str]:
    return _has_core_success_shape(resp.json())


def validate_break_rule(resp: requests.Response) -> tuple[bool, str]:
    data = resp.json()
    ok, message = _has_core_success_shape(data)
    if not ok:
        return ok, message
    if not _contains_text_in_events(data, "30-minute required break"):
        return False, "Did not find required 30-minute break event."
    return True, "Detected 30-minute break event."


def validate_daily_reset_rule(resp: requests.Response) -> tuple[bool, str]:
    data = resp.json()
    ok, message = _has_core_success_shape(data)
    if not ok:
        return ok, message
    if not _contains_text_in_events(data, "10-hour reset"):
        return False, "Did not find 10-hour reset event."
    return True, "Detected 10-hour reset event."


def validate_cycle_limit_rule(resp: requests.Response) -> tuple[bool, str]:
    data = resp.json()
    ok, message = _has_core_success_shape(data)
    if not ok:
        return ok, message
    notes = data.get("summary", {}).get("compliance_notes", [])
    text = " ".join(str(item) for item in notes)
    if "70-hour/8-day limit reached" not in text:
        return False, "Did not find cycle limit compliance note."
    return True, "Detected cycle-limit compliance note."


def validate_fuel_rule(resp: requests.Response) -> tuple[bool, str]:
    data = resp.json()
    ok, message = _has_core_success_shape(data)
    if not ok:
        return ok, message
    if not _contains_text_in_events(data, "Fuel stop"):
        return False, "Did not find fuel-stop event."
    return True, "Detected fuel-stop event."


def validate_400_for_invalid_cycle(resp: requests.Response) -> tuple[bool, str]:
    try:
        payload = resp.json()
    except Exception:
        return False, "Expected JSON error payload."
    if "current_cycle_used_hours" not in payload:
        return False, f"Missing field error for current_cycle_used_hours. Payload: {payload}"
    return True, "Got field-level validation error."


def validate_400_for_missing_field(resp: requests.Response) -> tuple[bool, str]:
    payload = resp.json()
    if "pickup_location" not in payload:
        return False, f"Missing pickup_location validation error. Payload: {payload}"
    return True, "Got missing-field validation error."


def validate_400_for_bad_geocode(resp: requests.Response) -> tuple[bool, str]:
    payload = resp.json()
    detail = str(payload.get("detail", ""))
    if not detail:
        return False, f"Expected detail message. Payload: {payload}"
    return True, f"Got geocode failure detail: {detail}"


def build_test_cases() -> list[TestCase]:
    return [
        TestCase(
            name="Success: Happy Path",
            payload={
                "current_location": "Atlanta, GA",
                "pickup_location": "Nashville, TN",
                "dropoff_location": "Chicago, IL",
                "current_cycle_used_hours": 12,
            },
            expected_status=200,
            validator=validate_happy_path,
        ),
        TestCase(
            name="Breaking Point: 8h Driving Break",
            payload={
                "current_location": "Los Angeles, CA",
                "pickup_location": "Las Vegas, NV",
                "dropoff_location": "Denver, CO",
                "current_cycle_used_hours": 10,
            },
            expected_status=200,
            validator=validate_break_rule,
        ),
        TestCase(
            name="Breaking Point: 11h/14h Daily Reset",
            payload={
                "current_location": "Miami, FL",
                "pickup_location": "Atlanta, GA",
                "dropoff_location": "New York, NY",
                "current_cycle_used_hours": 20,
            },
            expected_status=200,
            validator=validate_daily_reset_rule,
        ),
        TestCase(
            name="Breaking Point: 70h Cycle Limit",
            payload={
                "current_location": "Dallas, TX",
                "pickup_location": "Oklahoma City, OK",
                "dropoff_location": "Chicago, IL",
                "current_cycle_used_hours": 68,
            },
            expected_status=200,
            validator=validate_cycle_limit_rule,
        ),
        TestCase(
            name="Breaking Point: Fuel Stop 1000+ Miles",
            payload={
                "current_location": "Seattle, WA",
                "pickup_location": "Boise, ID",
                "dropoff_location": "Houston, TX",
                "current_cycle_used_hours": 5,
            },
            expected_status=200,
            validator=validate_fuel_rule,
        ),
        TestCase(
            name="Validation Error: Invalid Cycle (<0)",
            payload={
                "current_location": "Atlanta, GA",
                "pickup_location": "Nashville, TN",
                "dropoff_location": "Chicago, IL",
                "current_cycle_used_hours": -1,
            },
            expected_status=400,
            validator=validate_400_for_invalid_cycle,
        ),
        TestCase(
            name="Validation Error: Missing Pickup",
            payload={
                "current_location": "Atlanta, GA",
                "dropoff_location": "Chicago, IL",
                "current_cycle_used_hours": 10,
            },
            expected_status=400,
            validator=validate_400_for_missing_field,
        ),
        TestCase(
            name="Validation Error: Bad Geocode",
            payload={
                "current_location": "ZZZ__NO_SUCH_CITY_12345",
                "pickup_location": "Nashville, TN",
                "dropoff_location": "Chicago, IL",
                "current_cycle_used_hours": 10,
            },
            expected_status=400,
            validator=validate_400_for_bad_geocode,
        ),
    ]


def run_suite(base_url: str, timeout: int) -> int:
    endpoint = f"{base_url.rstrip('/')}/api/trips/plan"
    tests = build_test_cases()
    session = requests.Session()

    print(f"Running {len(tests)} regression tests against {endpoint}\n")

    passed = 0
    failed = 0

    for index, test in enumerate(tests, start=1):
        started_at = time.time()
        try:
            response = session.post(endpoint, json=test.payload, timeout=timeout)
        except requests.RequestException as exc:
            failed += 1
            print(f"[{index:02d}] FAIL - {test.name}")
            print(f"     Request error: {exc}\n")
            continue

        elapsed = time.time() - started_at

        if response.status_code != test.expected_status:
            failed += 1
            print(f"[{index:02d}] FAIL - {test.name}")
            print(
                f"     Expected status {test.expected_status}, got {response.status_code} "
                f"in {elapsed:.2f}s"
            )
            print(f"     Body: {response.text[:400]}\n")
            continue

        try:
            is_valid, message = test.validator(response)
        except Exception as exc:
            failed += 1
            print(f"[{index:02d}] FAIL - {test.name}")
            print(f"     Validator crashed: {exc}")
            print(f"     Body: {response.text[:400]}\n")
            continue

        if is_valid:
            passed += 1
            print(f"[{index:02d}] PASS - {test.name} ({elapsed:.2f}s)")
            print(f"     {message}\n")
        else:
            failed += 1
            print(f"[{index:02d}] FAIL - {test.name} ({elapsed:.2f}s)")
            print(f"     {message}")
            try:
                compact = json.dumps(response.json(), indent=2)[:700]
                print(f"     Response excerpt: {compact}\n")
            except Exception:
                print(f"     Response text: {response.text[:700]}\n")

    print("=" * 72)
    print(f"Regression summary: PASS={passed}, FAIL={failed}, TOTAL={len(tests)}")
    print("=" * 72)
    return 0 if failed == 0 else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run HOS API regression test suite.")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL of backend server (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=90,
        help="Timeout (seconds) per request (default: 90)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    sys.exit(run_suite(base_url=args.base_url, timeout=args.timeout))

