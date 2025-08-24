from celery import shared_task
from .models import Vote
from .selenium_worker import (
    start_vote_session, click_captcha_and_send_sms,
    verify_otp, close_vote_session
)

@shared_task(bind=True, max_retries=2, default_retry_delay=5, queue="selenium")
def selenium_vote_start(self, vote_id: int):
    vote = Vote.objects.get(pk=vote_id)
    try:
        vote.status = "PROCESSING"
        vote.error_message = ""
        vote.save(update_fields=["status", "error_message"])

        info = start_vote_session(vote.id, vote.phone_snapshot)
        vote.captcha_width = info.width
        vote.captcha_height = info.height
        vote.captcha_image_b64 = f"data:image/png;base64,{info.image_b64}"
        vote.status = "CAPTCHA_READY"
        vote.save(update_fields=["status","captcha_width","captcha_height","captcha_image_b64"])
        return {"width": info.width, "height": info.height}

    except Exception as e:
        vote.status = "FAILED"
        vote.error_message = str(e)
        vote.save(update_fields=["status", "error_message"])
        raise

@shared_task(bind=True, queue="selenium")
def selenium_vote_click_and_send(self, vote_id: int, x: int, y: int):
    vote = Vote.objects.get(pk=vote_id)
    try:
        if vote.status not in ("CAPTCHA_READY", "PROCESSING"):
            raise RuntimeError(f"Invalid status for click: {vote.status}")
        vote.status = "PROCESSING"
        vote.save(update_fields=["status"])

        click_captcha_and_send_sms(vote.id, x, y)
        vote.status = "OTP_REQUIRED"
        vote.save(update_fields=["status"])
        return {"ok": True}

    except Exception as e:
        vote.status = "FAILED"
        vote.error_message = str(e)
        vote.save(update_fields=["status", "error_message"])
        raise

@shared_task(bind=True, queue="selenium")
def selenium_vote_verify_otp(self, vote_id: int, code: str):
    vote = Vote.objects.get(pk=vote_id)
    try:
        if vote.status != "OTP_REQUIRED":
            raise RuntimeError(f"Invalid status for otp: {vote.status}")
        vote.status = "PROCESSING"
        vote.save(update_fields=["status"])

        ok = verify_otp(vote.id, code)
        vote.status = "SUCCESS" if ok else "FAILED"
        vote.save(update_fields=["status"])
        return {"ok": ok}

    except Exception as e:
        vote.status = "FAILED"
        vote.error_message = str(e)
        vote.save(update_fields=["status", "error_message"])
        raise

@shared_task(bind=True, queue="selenium")
def selenium_vote_cleanup(self, vote_id: int):
    try:
        close_vote_session(vote_id)
        return {"closed": True}
    except Exception:
        return {"closed": False}
