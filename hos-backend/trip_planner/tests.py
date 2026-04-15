from unittest.mock import patch

from django.urls import reverse
from rest_framework.test import APITestCase


class TripPlanAPITests(APITestCase):
    @patch("trip_planner.services.fetch_route_leg")
    @patch("trip_planner.services.geocode_location")
    def test_trip_plan_returns_timeline_and_daily_logs(
        self, mock_geocode_location, mock_fetch_route_leg
    ):
        mock_geocode_location.side_effect = [
            (33.7490, -84.3880, "Atlanta, GA"),
            (36.1627, -86.7816, "Nashville, TN"),
            (41.8781, -87.6298, "Chicago, IL"),
        ]
        from trip_planner.services import RouteLeg

        mock_fetch_route_leg.side_effect = [
            RouteLeg(
                "Atlanta, GA",
                "Nashville, TN",
                250.0,
                5.0,
                [[-84.38, 33.74], [-86.78, 36.16]],
                ["Head north on I-75 for 10 mi"],
            ),
            RouteLeg(
                "Nashville, TN",
                "Chicago, IL",
                470.0,
                9.0,
                [[-86.78, 36.16], [-87.62, 41.87]],
                ["Continue on I-65 for 30 mi"],
            ),
        ]

        response = self.client.post(
            reverse("trip-plan"),
            {
                "current_location": "Atlanta, GA",
                "pickup_location": "Nashville, TN",
                "dropoff_location": "Chicago, IL",
                "current_cycle_used_hours": 12,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("timeline", response.data)
        self.assertIn("daily_logs", response.data)
        self.assertGreater(len(response.data["timeline"]), 0)
        self.assertGreater(len(response.data["daily_logs"]), 0)
