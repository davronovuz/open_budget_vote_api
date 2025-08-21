from celery import shared_task
import time

@shared_task
def test_task():
    time.sleep(5)
    return "Celery ishladi!"


from celery import shared_task
from django.utils import timezone
from .models import Vote
from .selenium_worker import run_vote_process


@shared_task
def selenium_vote_start(vote_id: int):
    try:
        vote = Vote.objects.get(id=vote_id)
        vote.status = "PROCESSING"
        vote.save(update_fields=["status"])

        # Selenium ishga tushiramiz
        success = run_vote_process(vote.phone_snapshot)

        if success:
            vote.status = "OTP_REQUIRED"  # SMS yuborildi
        else:
            vote.status = "FAILED"
            vote.error_message = "Selenium jarayonida xato"
        vote.save(update_fields=["status", "error_message"])

    except Vote.DoesNotExist:
        return
