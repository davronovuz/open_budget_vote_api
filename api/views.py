from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from .serializers import VoteStartSerializer
from .models import Vote
from .tasks import selenium_vote_start  # Celery task


class VoteStartView(APIView):
    """
    POST /api/v1/voting/start/
    body: { "project_id": 1, "phone": "+998901234567" }
    """

    def post(self, request):
        serializer = VoteStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project = serializer.validated_data["project"]
        phone = serializer.validated_data["phone"]

        # Vote yaratamiz
        vote = Vote.objects.create(
            project=project,
            phone_snapshot=phone,
            status="PENDING",
            created_at=timezone.now()
        )

        # Celery job chaqiramiz
        selenium_vote_start.delay(vote.id)

        return Response(
            {"message": "✅ Ovoz jarayoni boshlandi. SMS kodi kutilmoqda.", "vote_id": vote.id},
            status=status.HTTP_201_CREATED
        )
