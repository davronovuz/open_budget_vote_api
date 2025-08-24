from rest_framework import serializers
from .models import Project, Vote
import re

class VoteStartSerializer(serializers.Serializer):
    project_id = serializers.IntegerField()
    phone = serializers.CharField()
    telegram_id = serializers.IntegerField()

    def validate(self, attrs):
        pid = attrs["project_id"]
        try:
            project = Project.objects.get(pk=pid)
        except Project.DoesNotExist:
            raise serializers.ValidationError({"project_id": "Project not found"})
        phone = attrs["phone"].strip().replace(" ", "").replace("-", "")
        if not re.fullmatch(r"^\+?998\d{9}$", phone):
            raise serializers.ValidationError({"phone": "Phone must be like +998901234567"})
        if not phone.startswith("+"):
            phone = "+" + phone
        attrs["phone"] = phone
        attrs["project"] = project
        return attrs

class VoteDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = ("id","telegram_id","status","error_message",
                  "captcha_width","captcha_height","captcha_image_b64","created_at")

class CaptchaSnapshotSerializer(serializers.Serializer):
    vote_id = serializers.IntegerField()

class CaptchaClickSerializer(serializers.Serializer):
    vote_id = serializers.IntegerField()
    x = serializers.IntegerField(min_value=0)
    y = serializers.IntegerField(min_value=0)

class OTPVerifySerializer(serializers.Serializer):
    vote_id = serializers.IntegerField()
    code = serializers.CharField(min_length=3, max_length=12)
