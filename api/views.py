from django.utils import timezone
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Vote
from .serializers import (
    VoteStartSerializer, VoteDetailSerializer,
    CaptchaSnapshotSerializer, CaptchaClickSerializer, OTPVerifySerializer
)
from .tasks import (
    selenium_vote_start, selenium_vote_click_and_send,
    selenium_vote_verify_otp, selenium_vote_cleanup
)

class VoteStartView(APIView):
    """
    POST /api/vote/start/
    body: { "project_id": 1, "phone": "+998901234567", "telegram_id": 123 }
    """
    def post(self, request):
        s = VoteStartSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        project = s.validated_data["project"]
        phone = s.validated_data["phone"]
        telegram_id = s.validated_data["telegram_id"]

        with transaction.atomic():
            vote = Vote.objects.create(
                project=project,
                phone_snapshot=phone,
                telegram_id=telegram_id,
                status="PENDING",
                created_at=timezone.now()
            )
        return Response(
            {"message": "✅ Jarayon boshlandi. Captcha snapshot chaqiring.",
             "vote_id": vote.id, "status": vote.status},
            status=status.HTTP_201_CREATED
        )

class VoteDetailView(APIView):
    """GET /api/vote/{vote_id}/"""
    def get(self, request, vote_id: int):
        try:
            vote = Vote.objects.get(pk=vote_id)
        except Vote.DoesNotExist:
            return Response({"detail":"Not found"}, status=404)
        return Response(VoteDetailSerializer(vote).data)

class VoteCaptchaSnapshotView(APIView):
    """POST /api/vote/captcha/snapshot/  body: {vote_id}"""
    def post(self, request):
        s = CaptchaSnapshotSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        vote_id = s.validated_data["vote_id"]

        try:
            vote = Vote.objects.get(pk=vote_id)
        except Vote.DoesNotExist:
            return Response({"detail":"Vote not found"}, status=404)

        if vote.status == "CAPTCHA_READY":
            return Response({
                "status": vote.status,
                "width": vote.captcha_width,
                "height": vote.captcha_height,
                "image_b64": vote.captcha_image_b64,
            })

        if vote.status not in ("PENDING","PROCESSING","FAILED"):
            return Response({"detail": f"Invalid status: {vote.status}"}, status=400)

        vote.status = "PROCESSING"
        vote.error_message = ""
        vote.save(update_fields=["status","error_message"])
        selenium_vote_start.delay(vote_id)

        return Response({"status":"PROCESSING","message":"📸 Snapshot tayyorlanmoqda"}, status=202)

class VoteCaptchaClickView(APIView):
    """POST /api/vote/captcha/click/  body: {vote_id, x, y}"""
    def post(self, request):
        s = CaptchaClickSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        vote_id = s.validated_data["vote_id"]
        x = s.validated_data["x"]
        y = s.validated_data["y"]

        try:
            vote = Vote.objects.get(pk=vote_id)
        except Vote.DoesNotExist:
            return Response({"detail":"Vote not found"}, status=404)

        if vote.status not in ("CAPTCHA_READY","PROCESSING"):
            return Response({"detail": f"Invalid status: {vote.status}"}, status=400)

        vote.status = "PROCESSING"
        vote.save(update_fields=["status"])
        selenium_vote_click_and_send.delay(vote_id, x, y)

        return Response({"status":"PROCESSING","message":"🖱️ Nuqta yuborildi, SMS yuborilmoqda"}, status=202)

class VoteOtpVerifyView(APIView):
    """POST /api/vote/otp/verify/  body:{vote_id, code}"""
    def post(self, request):
        s = OTPVerifySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        vote_id = s.validated_data["vote_id"]
        code = s.validated_data["code"].strip()

        try:
            vote = Vote.objects.get(pk=vote_id)
        except Vote.DoesNotExist:
            return Response({"detail":"Vote not found"}, status=404)

        if vote.status != "OTP_REQUIRED":
            return Response({"detail": f"Invalid status: {vote.status}"}, status=400)

        vote.status = "PROCESSING"
        vote.save(update_fields=["status"])
        selenium_vote_verify_otp.delay(vote_id, code)

        return Response({"status":"PROCESSING","message":"🔐 OTP tekshirilmoqda"}, status=202)

class VoteCancelView(APIView):
    """POST /api/vote/cancel/  body:{vote_id}"""
    def post(self, request):
        s = CaptchaSnapshotSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        vote_id = s.validated_data["vote_id"]

        try:
            vote = Vote.objects.get(pk=vote_id)
        except Vote.DoesNotExist:
            return Response({"detail":"Vote not found"}, status=404)

        selenium_vote_cleanup.delay(vote_id)
        vote.status = "FAILED"
        vote.error_message = (vote.error_message or "") + "\nCancelled by user"
        vote.save(update_fields=["status","error_message"])
        return Response({"status": vote.status}, status=200)
