from django.urls import path
from .views import (
    VoteStartView, VoteDetailView,
    VoteCaptchaSnapshotView, VoteCaptchaClickView,
    VoteOtpVerifyView, VoteCancelView
)

urlpatterns = [
    path("vote/start/", VoteStartView.as_view()),
    path("vote/<int:vote_id>/", VoteDetailView.as_view()),
    path("vote/captcha/snapshot/", VoteCaptchaSnapshotView.as_view()),
    path("vote/captcha/click/", VoteCaptchaClickView.as_view()),
    path("vote/otp/verify/", VoteOtpVerifyView.as_view()),
    path("vote/cancel/", VoteCancelView.as_view()),
]
