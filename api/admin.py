# admin.py

import csv
from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html, format_html_join

from .models import Project, Vote, OtpAttempt, SeleniumJob, Setting


# ================== EXPORT HELPERS ==================
def export_votes_csv(modeladmin, request, queryset):
    """
    Tanlangan loyihalarga tegishli ovozlarni CSV faylga eksport qiladi.
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=votes_export.csv"

    writer = csv.writer(response)
    writer.writerow([
        "Project ID", "Project Title", "User", "Phone",
        "Status", "Error", "Created At"
    ])

    # barcha tanlangan loyihalarning ovozlarini chiqaramiz
    for project in queryset:
        for vote in project.votes.select_related("user"):
            writer.writerow([
                project.id,
                project.title,
                str(vote.user),
                vote.phone_snapshot,
                vote.status,
                vote.error_message or "",
                vote.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ])

    return response


export_votes_csv.short_description = "📥 Tanlangan loyihalarning ovozlarini CSV qilib yuklab olish"


# ================== INLINE'LAR ==================
class VoteInline(admin.TabularInline):
    model = Vote
    extra = 0
    readonly_fields = ("user", "phone_snapshot", "status", "created_at")
    fields = ("user", "phone_snapshot", "status", "created_at")
    can_delete = False


class OtpAttemptInline(admin.TabularInline):
    model = OtpAttempt
    extra = 0
    readonly_fields = ("code_entered", "result", "created_at")
    fields = ("code_entered", "result", "created_at")
    can_delete = False


class SeleniumJobInline(admin.TabularInline):
    model = SeleniumJob
    extra = 0
    readonly_fields = ("status", "node", "error", "created_at")
    fields = ("status", "node", "error", "created_at")
    can_delete = False


# ================== ADMIN'LAR ==================
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "id", "title", "region", "district", "category",
        "is_active", "reward_sum", "target_votes", "created_at"
    )
    list_filter = ("is_active", "region", "district", "category")
    search_fields = ("title", "ob_project_id")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "stats_summary")

    inlines = [VoteInline]

    actions = [export_votes_csv]  # ✅ CSV export qo‘shildi

    def stats_summary(self, obj):
        """Loyihaga oid ovozlarning to‘liq statistikasi"""
        total_votes = obj.votes.count()
        success_votes = obj.votes.filter(status="SUCCESS").count()
        failed_votes = obj.votes.filter(status="FAILED").count()
        otp_required = obj.votes.filter(status="OTP_REQUIRED").count()

        rows = format_html_join(
            "\n",
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>",
            (
                (v.user, v.phone_snapshot, v.status, v.created_at.strftime("%Y-%m-%d %H:%M"))
                for v in obj.votes.select_related("user").order_by("-created_at")
            )
        )

        return format_html(
            f"""
            <b>Umumiy ovozlar:</b> {total_votes}<br>
            ✅ Muvaffaqiyatli: {success_votes}<br>
            ❌ Xato: {failed_votes}<br>
            ⏳ OTP kutilmoqda: {otp_required}<br><br>

            <b>📋 Barcha ovozlar:</b>
            <table border="1" cellspacing="0" cellpadding="4">
              <tr>
                <th>Foydalanuvchi</th>
                <th>Telefon</th>
                <th>Status</th>
                <th>Sana/Vaqt</th>
              </tr>
              {rows}
            </table>
            """
        )

    stats_summary.short_description = "📊 Statistika"


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "project", "phone_snapshot", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("phone_snapshot", "error_message")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)

    inlines = [OtpAttemptInline, SeleniumJobInline]


@admin.register(OtpAttempt)
class OtpAttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "vote", "code_entered", "result", "created_at")
    list_filter = ("result",)
    search_fields = ("code_entered",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)


@admin.register(SeleniumJob)
class SeleniumJobAdmin(admin.ModelAdmin):
    list_display = ("id", "vote", "status", "node", "error", "created_at")
    list_filter = ("status", "node")
    search_fields = ("error",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)


@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ("id", "active_project", "default_reward_sum",
                    "allow_multiple_active_projects", "created_at")
    readonly_fields = ("created_at",)
