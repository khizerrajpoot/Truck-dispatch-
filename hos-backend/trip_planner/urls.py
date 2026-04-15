from django.urls import path

from .views import TripPlanAPIView


urlpatterns = [
    path("trips/plan", TripPlanAPIView.as_view(), name="trip-plan"),
]

