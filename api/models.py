from django.db import models
from django.utils import timezone

# ======== Helpers: CHOICES ========
VOTE_STATUS = (
    ("PENDING", "PENDING"),  # yaratildi, hali yuborilmadi
    ("OTP_REQUIRED", "OTP_REQUIRED"),  # SMS yuborildi, kod kutilmoqda
    ("PROCESSING", "PROCESSING"),  # Selenium/proxy ish qilmoqda
    ("SUCCESS", "SUCCESS"),  # muvaffaqiyatli ovoz berildi
    ("FAILED", "FAILED"),  # xato (OTP noto‘g‘ri, captcha xato...)
)

OTP_RESULT = (
    ("OK", "OK"),
    ("WRONG", "WRONG"),
    ("EXPIRED", "EXPIRED"),
    ("ERROR", "ERROR"),
)


class Project(models.Model):
    """Ovoz berish mumkin bo‘lgan loyihalar (openbudget.uz dan)."""
    id = models.AutoField(primary_key=True)
    ob_project_id = models.CharField(max_length=64)  # openbudget.uz dagi ID
    title = models.CharField(max_length=255)
    url = models.CharField(max_length=1024)
    region = models.CharField(max_length=128, null=True, blank=True)
    district = models.CharField(max_length=128, null=True, blank=True)
    category = models.CharField(max_length=128, null=True, blank=True)
    is_active = models.BooleanField(default=False)
    reward_sum = models.IntegerField(default=0)  # ovoz uchun mukofot UZS
    target_votes = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "projects"
        indexes = [
            models.Index(fields=["is_active"], name="ix_projects_active"),
            models.Index(fields=["category"], name="ix_projects_category"),
        ]

    def __str__(self):
        return f"[{self.id}] {self.title}"


class Vote(models.Model):
    """Foydalanuvchining loyiha uchun bergan ovozi."""
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        "User", on_delete=models.CASCADE, db_column="user_id", related_name="votes"
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, db_column="project_id", related_name="votes"
    )
    user_phone_id = models.IntegerField(null=True, blank=True)  # UserPhone.id snapshot
    phone_snapshot = models.CharField(max_length=24)  # ovoz paytidagi telefon
    status = models.CharField(max_length=24, choices=VOTE_STATUS, default="PENDING")
    attempt_count = models.IntegerField(default=0)
    selenium_session_id = models.CharField(max_length=128, null=True, blank=True)
    ob_vote_id = models.CharField(max_length=64, null=True, blank=True)  # openbudget ovoz ID
    proof_screenshot_path = models.CharField(max_length=1024, null=True, blank=True)
    error_message = models.CharField(max_length=512, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "votes"
        indexes = [
            models.Index(fields=["project", "status"], name="ix_votes_project_status"),
            models.Index(fields=["user"], name="ix_votes_user"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "phone_snapshot"], name="uq_vote_phone_per_project"
            ),
            models.UniqueConstraint(
                fields=["project", "user_phone_id"], name="uq_vote_userphone_per_project"
            ),
        ]


class OtpAttempt(models.Model):
    """Har bir OTP kodini urinishlar logi."""
    id = models.AutoField(primary_key=True)
    vote = models.ForeignKey(
        Vote, on_delete=models.CASCADE, db_column="vote_id", related_name="otp_attempts"
    )
    code_entered = models.CharField(max_length=16)
    result = models.CharField(max_length=16, choices=OTP_RESULT)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "otpattempts"


class SeleniumJob(models.Model):
    """Ovoz berish uchun Selenium ishchi vazifa logi."""
    id = models.AutoField(primary_key=True)
    vote = models.ForeignKey(
        Vote, on_delete=models.CASCADE, db_column="vote_id", related_name="selenium_jobs"
    )
    status = models.CharField(
        max_length=16, choices=(("QUEUED", "QUEUED"), ("RUNNING", "RUNNING"),
                                ("DONE", "DONE"), ("FAILED", "FAILED")),
        default="QUEUED"
    )
    node = models.CharField(max_length=64, null=True, blank=True)  # Selenium node nomi
    timings = models.JSONField(null=True, blank=True)  # bosqichlar vaqti
    error = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "seleniumjobs"

class Setting(models.Model):
    """Admin tomonidan global sozlamalar."""
    id = models.AutoField(primary_key=True)
    active_project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, null=True, db_column="active_project_id"
    )
    default_reward_sum = models.IntegerField(default=0)
    allow_multiple_active_projects = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "settings"
