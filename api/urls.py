from .views import VoteStartView
from django.urls import path


urlpatterns=[
    path("vote/start/", VoteStartView.as_view(), name="vote_start"),
]