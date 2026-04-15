from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
from typing import Any

import requests


HOURS_PER_BREAK = 0.5
HOURS_PER_PICKUP_DROPOFF = 1.0
HOURS_PER_FUEL_STOP = 0.5
FUEL_INTERVAL_MILES = 1000.0
MAX_DRIVE_HOURS_PER_DUTY = 11.0
MAX_DUTY_WINDOW_HOURS = 14.0
MAX_DRIVE_BEFORE_BREAK = 8.0
OFF_DUTY_RESET_HOURS = 10.0
CYCLE_LIMIT_HOURS = 70.0
RESTART_HOURS = 34.0
FALLBACK_SPEED_MPH = 50.0

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
OSRM_ROUTE_URL = "https://router.project-osrm.org/route/v1/driving/{start};{end}"


class TripPlanningError(Exception):
    """Raised when required route/geocode data cannot be generated."""


@dataclass
class RouteLeg:
    origin: str
    destination: str
    distance_miles: float
    drive_hours: float
    geometry: list[list[float]]
    steps: list[str]


class TripPlanner:
    def __init__(self, start_datetime: datetime, current_cycle_used_hours: float) -> None:
        self.current_time = start_datetime
        self.events: list[dict[str, Any]] = []
        self.total_distance_miles = 0.0
        self.total_drive_hours = 0.0

        self.daily_drive_hours = 0.0
        self.daily_duty_window_hours = 0.0
        self.drive_since_break_hours = 0.0

        self.cycle_on_duty_hours = current_cycle_used_hours
        self.compliance_notes: list[str] = []

    def add_event(self, status: str, duration_hours: float, location: str, notes: str) -> None:
        if duration_hours <= 0:
            return

        start_at = self.current_time
        end_at = self.current_time + timedelta(hours=duration_hours)
        self.events.append(
            {
                "status": status,
                "start": start_at.isoformat(),
                "end": end_at.isoformat(),
                "duration_hours": round(duration_hours, 2),
                "location": location,
                "notes": notes,
            }
        )
        self.current_time = end_at

    def _consume_on_duty(self, hours: float) -> None:
        self.daily_duty_window_hours += hours
        self.cycle_on_duty_hours += hours

    def _ensure_cycle_capacity(self, location: str) -> None:
        if self.cycle_on_duty_hours < CYCLE_LIMIT_HOURS:
            return

        self.compliance_notes.append(
            "70-hour/8-day limit reached, applying 34-hour restart to continue trip."
        )
        self.add_event(
            status="OFF_DUTY",
            duration_hours=RESTART_HOURS,
            location=location,
            notes="34-hour restart due to cycle limit.",
        )
        self.daily_drive_hours = 0.0
        self.daily_duty_window_hours = 0.0
        self.drive_since_break_hours = 0.0
        self.cycle_on_duty_hours = 0.0

    def add_on_duty_event(self, duration_hours: float, location: str, notes: str) -> None:
        self._ensure_cycle_capacity(location)
        available_cycle_hours = CYCLE_LIMIT_HOURS - self.cycle_on_duty_hours
        if duration_hours > available_cycle_hours:
            self._ensure_cycle_capacity(location)
        self.add_event("ON_DUTY_NOT_DRIVING", duration_hours, location, notes)
        self._consume_on_duty(duration_hours)

    def enforce_daily_reset_if_needed(self, location: str) -> None:
        if (
            self.daily_drive_hours >= MAX_DRIVE_HOURS_PER_DUTY
            or self.daily_duty_window_hours >= MAX_DUTY_WINDOW_HOURS
        ):
            self.add_event(
                status="OFF_DUTY",
                duration_hours=OFF_DUTY_RESET_HOURS,
                location=location,
                notes="10-hour reset due to 11-hour drive or 14-hour duty window limit.",
            )
            self.daily_drive_hours = 0.0
            self.daily_duty_window_hours = 0.0
            self.drive_since_break_hours = 0.0

    def drive_leg(
        self,
        leg: RouteLeg,
        fuel_miles_since_last_stop: float,
    ) -> float:
        remaining_hours = leg.drive_hours
        remaining_miles = leg.distance_miles
        miles_per_hour = (
            leg.distance_miles / leg.drive_hours if leg.drive_hours > 0 else FALLBACK_SPEED_MPH
        )

        while remaining_hours > 0.0001:
            self._ensure_cycle_capacity(leg.origin)
            self.enforce_daily_reset_if_needed(leg.origin)

            if self.drive_since_break_hours >= MAX_DRIVE_BEFORE_BREAK:
                self.add_on_duty_event(
                    duration_hours=HOURS_PER_BREAK,
                    location=leg.origin,
                    notes="30-minute required break after 8 cumulative driving hours.",
                )
                self.drive_since_break_hours = 0.0
                continue

            max_chunk = min(
                remaining_hours,
                MAX_DRIVE_HOURS_PER_DUTY - self.daily_drive_hours,
                MAX_DUTY_WINDOW_HOURS - self.daily_duty_window_hours,
                MAX_DRIVE_BEFORE_BREAK - self.drive_since_break_hours,
                CYCLE_LIMIT_HOURS - self.cycle_on_duty_hours,
            )

            if max_chunk <= 0:
                self.enforce_daily_reset_if_needed(leg.origin)
                if self.cycle_on_duty_hours >= CYCLE_LIMIT_HOURS:
                    self._ensure_cycle_capacity(leg.origin)
                continue

            chunk_miles = min(remaining_miles, max_chunk * miles_per_hour)
            self.add_event(
                status="DRIVING",
                duration_hours=max_chunk,
                location=leg.destination,
                notes=f"Driving toward {leg.destination}.",
            )

            self.daily_drive_hours += max_chunk
            self.drive_since_break_hours += max_chunk
            self._consume_on_duty(max_chunk)
            self.total_drive_hours += max_chunk
            self.total_distance_miles += chunk_miles
            remaining_hours -= max_chunk
            remaining_miles = max(0.0, remaining_miles - chunk_miles)
            fuel_miles_since_last_stop += chunk_miles

            while fuel_miles_since_last_stop >= FUEL_INTERVAL_MILES:
                self.add_on_duty_event(
                    duration_hours=HOURS_PER_FUEL_STOP,
                    location=leg.destination,
                    notes="Fuel stop (required at least every 1,000 miles).",
                )
                fuel_miles_since_last_stop -= FUEL_INTERVAL_MILES

        return fuel_miles_since_last_stop


def geocode_location(location: str) -> tuple[float, float, str]:
    response = requests.get(
        NOMINATIM_SEARCH_URL,
        params={"q": location, "format": "json", "limit": 1},
        headers={"User-Agent": "ghani-trip-planner/1.0"},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    if not data:
        raise TripPlanningError(f"Could not geocode location: {location}")
    first = data[0]
    return float(first["lat"]), float(first["lon"]), first.get("display_name", location)


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_miles = 3958.8
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_miles * c


def fetch_route_leg(
    origin_name: str,
    destination_name: str,
    origin_coords: tuple[float, float],
    destination_coords: tuple[float, float],
) -> RouteLeg:
    origin_lat, origin_lon = origin_coords
    destination_lat, destination_lon = destination_coords

    start = f"{origin_lon},{origin_lat}"
    end = f"{destination_lon},{destination_lat}"
    url = OSRM_ROUTE_URL.format(start=start, end=end)

    try:
        response = requests.get(
            url,
            params={"overview": "full", "geometries": "geojson", "steps": "true"},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        routes = payload.get("routes", [])
        if not routes:
            raise TripPlanningError("OSRM route response was empty.")
        route = routes[0]
        distance_miles = route["distance"] / 1609.344
        drive_hours = route["duration"] / 3600
        geometry = route["geometry"]["coordinates"]
        steps = []
        for leg in route.get("legs", []):
            for step in leg.get("steps", []):
                maneuver = step.get("maneuver", {}).get("type", "continue").replace("_", " ")
                road = step.get("name") or "unnamed road"
                step_miles = step.get("distance", 0) / 1609.344
                steps.append(f"{maneuver.title()} onto {road} for {step_miles:.2f} mi")
        return RouteLeg(
            origin=origin_name,
            destination=destination_name,
            distance_miles=distance_miles,
            drive_hours=drive_hours,
            geometry=geometry,
            steps=steps,
        )
    except (requests.RequestException, KeyError, TripPlanningError):
        fallback_distance = haversine_miles(
            origin_lat, origin_lon, destination_lat, destination_lon
        ) * 1.2
        return RouteLeg(
            origin=origin_name,
            destination=destination_name,
            distance_miles=fallback_distance,
            drive_hours=fallback_distance / FALLBACK_SPEED_MPH,
            geometry=[[origin_lon, origin_lat], [destination_lon, destination_lat]],
            steps=[
                f"Drive from {origin_name} to {destination_name} (fallback route estimate).",
            ],
        )


def split_event_by_day(event: dict[str, Any]) -> list[dict[str, Any]]:
    start = datetime.fromisoformat(event["start"])
    end = datetime.fromisoformat(event["end"])
    if start.date() == end.date():
        return [event]

    segments = []
    cursor = start
    while cursor < end:
        next_midnight = (cursor + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        segment_end = min(next_midnight, end)
        duration = (segment_end - cursor).total_seconds() / 3600
        segments.append(
            {
                **event,
                "start": cursor.isoformat(),
                "end": segment_end.isoformat(),
                "duration_hours": round(duration, 2),
            }
        )
        cursor = segment_end
    return segments


def build_daily_logs(events: list[dict[str, Any]], trip_inputs: dict[str, Any]) -> list[dict[str, Any]]:
    by_day: dict[str, dict[str, Any]] = {}
    status_map = {
        "OFF_DUTY": "off_duty_hours",
        "SLEEPER": "sleeper_hours",
        "DRIVING": "driving_hours",
        "ON_DUTY_NOT_DRIVING": "on_duty_not_driving_hours",
    }

    for original_event in events:
        for event in split_event_by_day(original_event):
            start_dt = datetime.fromisoformat(event["start"])
            day_key = start_dt.date().isoformat()
            day = by_day.setdefault(
                day_key,
            {
                    "date": day_key,
                    "off_duty_hours": 0.0,
                    "sleeper_hours": 0.0,
                    "driving_hours": 0.0,
                    "on_duty_not_driving_hours": 0.0,
                    "remarks": [],
                    "events": [],
                },
            )
            bucket = status_map[event["status"]]
            day[bucket] += event["duration_hours"]
            day["remarks"].append(f'{event["location"]} - {event["notes"]}')
            day["events"].append(event)

    return render_daily_log_images(by_day, trip_inputs)


def render_daily_log_images(by_day: dict[str, dict[str, Any]], trip_inputs: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _render_one_day_log(
            entry=entry,
            trip_inputs=trip_inputs,
        )
        for _, entry in sorted(by_day.items())
    ]


def _render_one_day_log(
    entry: dict[str, Any],
    trip_inputs: dict[str, Any],
) -> dict[str, Any]:
    date = datetime.fromisoformat(entry["date"])
    segments = []

    for event in entry["events"]:
        start_dt = datetime.fromisoformat(event["start"])
        end_dt = datetime.fromisoformat(event["end"])
        start_hour = start_dt.hour + start_dt.minute / 60.0
        end_hour = end_dt.hour + end_dt.minute / 60.0
        if end_hour < start_hour:
            end_hour = 24.0
        segments.append(
            {
                "status": event["status"],
                "start_hour": round(start_hour, 2),
                "end_hour": round(end_hour, 2),
                "location": event["location"],
                "notes": event["notes"],
            }
        )

    remarks_text = "; ".join(entry["remarks"][:4])[:220]
    status_totals = {
        "off_duty_hours": round(entry["off_duty_hours"], 2),
        "sleeper_hours": round(entry["sleeper_hours"], 2),
        "driving_hours": round(entry["driving_hours"], 2),
        "on_duty_not_driving_hours": round(entry["on_duty_not_driving_hours"], 2),
    }
    total_route_miles = float(trip_inputs.get("total_route_miles", 0.0) or 0.0)
    total_route_drive_hours = float(trip_inputs.get("total_route_drive_hours", 0.0) or 0.0)
    if total_route_drive_hours > 0:
        miles_today = round(
            (status_totals["driving_hours"] / total_route_drive_hours) * total_route_miles, 1
        )
    else:
        miles_today = 0.0

    total_hours = round(
        status_totals["off_duty_hours"]
        + status_totals["sleeper_hours"]
        + status_totals["driving_hours"]
        + status_totals["on_duty_not_driving_hours"],
        2,
    )

    return {
        "date": entry["date"],
        "off_duty_hours": status_totals["off_duty_hours"],
        "sleeper_hours": status_totals["sleeper_hours"],
        "driving_hours": status_totals["driving_hours"],
        "on_duty_not_driving_hours": status_totals["on_duty_not_driving_hours"],
        "total_hours": total_hours,
        "remarks": entry["remarks"],
        "log_sheet_data": {
            "month": date.strftime("%m"),
            "day": date.strftime("%d"),
            "year": date.strftime("%Y"),
            "driver_name": "System Generated Driver",
            "driver_signature": "System Generated Driver",
            "co_driver_name": "N/A",
            "carrier_name": "Assessment Carrier",
            "main_office_address": "N/A",
            "truck_or_tractor_numbers": "N/A",
            "trailer_numbers": "N/A",
            "shipping_document_number": "AUTO-GENERATED",
            "shipper_and_commodity": "Trip load / General freight",
            "total_miles_driving_today": miles_today,
            "from_location": trip_inputs["current_location"],
            "to_location": trip_inputs["dropoff_location"],
            "cycle_used_hours_start": trip_inputs["current_cycle_used_hours"],
            "remarks_text": remarks_text,
            "status_totals": status_totals,
            "segments": segments,
        },
    }


def extract_stop_rest_points(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    points = []
    keywords = ("break", "fuel", "pickup", "dropoff", "reset")
    for event in events:
        notes = str(event.get("notes", "")).lower()
        if any(word in notes for word in keywords):
            points.append(
                {
                    "time": event["start"],
                    "status": event["status"],
                    "location": event["location"],
                    "notes": event["notes"],
                }
            )
    return points


def build_route_instructions(legs: list[RouteLeg]) -> list[str]:
    instructions = []
    for idx, leg in enumerate(legs, start=1):
        instructions.append(f"Leg {idx}: {leg.origin} -> {leg.destination}")
        instructions.extend(leg.steps[:25])
    return instructions


def plan_trip(
    current_location: str,
    pickup_location: str,
    dropoff_location: str,
    current_cycle_used_hours: float,
    start_datetime: datetime | None = None,
) -> dict[str, Any]:
    if start_datetime is None:
        start_datetime = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    elif start_datetime.tzinfo is None:
        start_datetime = start_datetime.replace(tzinfo=timezone.utc)

    current_lat, current_lon, current_name = geocode_location(current_location)
    pickup_lat, pickup_lon, pickup_name = geocode_location(pickup_location)
    dropoff_lat, dropoff_lon, dropoff_name = geocode_location(dropoff_location)

    leg_to_pickup = fetch_route_leg(
        origin_name=current_name,
        destination_name=pickup_name,
        origin_coords=(current_lat, current_lon),
        destination_coords=(pickup_lat, pickup_lon),
    )
    leg_to_dropoff = fetch_route_leg(
        origin_name=pickup_name,
        destination_name=dropoff_name,
        origin_coords=(pickup_lat, pickup_lon),
        destination_coords=(dropoff_lat, dropoff_lon),
    )

    planner = TripPlanner(
        start_datetime=start_datetime,
        current_cycle_used_hours=current_cycle_used_hours,
    )

    fuel_miles = 0.0
    fuel_miles = planner.drive_leg(leg_to_pickup, fuel_miles)
    planner.add_on_duty_event(
        duration_hours=HOURS_PER_PICKUP_DROPOFF,
        location=pickup_name,
        notes="Pickup operation (fixed 1 hour).",
    )
    fuel_miles = planner.drive_leg(leg_to_dropoff, fuel_miles)
    planner.add_on_duty_event(
        duration_hours=HOURS_PER_PICKUP_DROPOFF,
        location=dropoff_name,
        notes="Dropoff operation (fixed 1 hour).",
    )

    total_route_miles = leg_to_pickup.distance_miles + leg_to_dropoff.distance_miles
    total_route_hours = leg_to_pickup.drive_hours + leg_to_dropoff.drive_hours

    trip_inputs = {
        "current_location": current_location,
        "pickup_location": pickup_location,
        "dropoff_location": dropoff_location,
        "current_cycle_used_hours": current_cycle_used_hours,
        "start_datetime": start_datetime.isoformat(),
        "total_route_miles": round(total_route_miles, 2),
        "total_route_drive_hours": round(total_route_hours, 2),
    }
    daily_logs = build_daily_logs(planner.events, trip_inputs)
    route_legs = [leg_to_pickup, leg_to_dropoff]

    return {
        "trip_inputs": trip_inputs,
        "assumptions": {
            "driver_type": "Property-carrying, 70-hour/8-day",
            "adverse_driving_conditions": False,
            "fuel_interval_miles": FUEL_INTERVAL_MILES,
            "pickup_duration_hours": HOURS_PER_PICKUP_DROPOFF,
            "dropoff_duration_hours": HOURS_PER_PICKUP_DROPOFF,
            "fuel_stop_duration_hours": HOURS_PER_FUEL_STOP,
        },
        "route": {
            "total_distance_miles": round(total_route_miles, 2),
            "total_drive_hours": round(total_route_hours, 2),
            "instructions": build_route_instructions(route_legs),
            "legs": [
                {
                    "origin": leg_to_pickup.origin,
                    "destination": leg_to_pickup.destination,
                    "distance_miles": round(leg_to_pickup.distance_miles, 2),
                    "drive_hours": round(leg_to_pickup.drive_hours, 2),
                    "geometry": leg_to_pickup.geometry,
                    "steps": leg_to_pickup.steps,
                },
                {
                    "origin": leg_to_dropoff.origin,
                    "destination": leg_to_dropoff.destination,
                    "distance_miles": round(leg_to_dropoff.distance_miles, 2),
                    "drive_hours": round(leg_to_dropoff.drive_hours, 2),
                    "geometry": leg_to_dropoff.geometry,
                    "steps": leg_to_dropoff.steps,
                },
            ],
        },
        "timeline": planner.events,
        "stops_and_rests": extract_stop_rest_points(planner.events),
        "daily_logs": daily_logs,
        "summary": {
            "planned_total_distance_miles": round(planner.total_distance_miles, 2),
            "planned_total_driving_hours": round(planner.total_drive_hours, 2),
            "planned_finish_time": planner.current_time.isoformat(),
            "cycle_hours_used_after_trip": round(planner.cycle_on_duty_hours, 2),
            "compliance_notes": planner.compliance_notes,
        },
    }

