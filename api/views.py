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
    body: { "project_id": 1, "phone": "+998901234567", "telegram_id": 123456789 }
    """

    def post(self, request):
        serializer = VoteStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project = serializer.validated_data["project"]
        phone = serializer.validated_data["phone"]
        telegram_id = serializer.validated_data["telegram_id"]

        vote = Vote.objects.create(
            project=project,
            phone_snapshot=phone,
            telegram_id=telegram_id,   # 🔑 qo‘shildi
            status="PENDING",
            created_at=timezone.now()
        )

        selenium_vote_start.delay(vote.id)

        return Response(
            {"message": "✅ Ovoz jarayoni boshlandi. SMS kodi kutilmoqda.", "vote_id": vote.id},
            status=status.HTTP_201_CREATED
        )

