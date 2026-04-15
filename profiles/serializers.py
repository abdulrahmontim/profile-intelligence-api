from rest_framework import serializers
from .models import Profile

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['id',
                  'name',
                  'gender',
                  'gender_probability',
                  'sample_size',
                  'age',
                  'age_group',
                  'country_id',
                  'country_probability',
                  'created_at']

        read_only_fields = ['id', 'created_at']