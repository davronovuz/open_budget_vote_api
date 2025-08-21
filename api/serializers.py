from rest_framework import serializers
from .models import Vote, Project


class VoteStartSerializer(serializers.Serializer):
    project_id = serializers.IntegerField()
    phone = serializers.CharField(max_length=24)
    telegram_id = serializers.IntegerField()

    def validate(self, data):
        project_id = data.get("project_id")
        phone = data.get("phone")

        # loyiha mavjudligini tekshirish
        try:
            project = Project.objects.get(id=project_id, is_active=True)
        except Project.DoesNotExist:
            raise serializers.ValidationError("❌ Loyiha topilmadi yoki aktiv emas.")

        # oldin ovoz berilganmi (unique constraintga tayyorlash)
        if Vote.objects.filter(project=project, phone_snapshot=phone).exists():
            raise serializers.ValidationError("❌ Bu telefon raqam allaqachon ovoz bergan.")

        data["project"] = project
        return data
