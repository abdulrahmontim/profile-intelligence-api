from rest_framework import serializers
from .models import Profile

class ProfileSerializer(serializers.ModelSerializer):
    gender_probability = serializers.FloatField()
    country_probability = serializers.FloatField()
    class Meta:
        model = Profile
        fields = '__all__'

        read_only_fields = ['id', 'created_at']


class ProfileListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['id', 'name', 'gender', 'age', 'age_group', 'country_id']