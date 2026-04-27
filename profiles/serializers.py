from rest_framework import serializers
from .models import Profile

class ProfileSerializer(serializers.ModelSerializer):
    gender_probability = serializers.DecimalField(max_digits=5, decimal_places=2, coerce_to_string=False)
    country_probability = serializers.DecimalField(max_digits=5, decimal_places=2, coerce_to_string=False)

    class Meta:
        model = Profile
        fields = [
            "id",
            "name",
            "gender",
            "gender_probability",
            "age",
            "age_group",
            "country_id",
            "country_name",
            "country_probability",
            "created_at",
        ]

        read_only_fields = ['id', 'created_at']


class ProfileListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['id', 'name', 'gender', 'age', 'age_group', 'country_id']