from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import TripPlanRequestSerializer
from .services import TripPlanningError, plan_trip


class TripPlanAPIView(APIView):
    def post(self, request):
        serializer = TripPlanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = plan_trip(**serializer.validated_data)
        except TripPlanningError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_200_OK)
