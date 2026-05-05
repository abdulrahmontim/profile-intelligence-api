from django.db import models
from uuid6 import uuid7

# Create your models here.
class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    name = models.CharField(max_length=255, unique=True)
    
    GENDER_CHOICES = [
       ("male", "Male"),
       ("female", "Female")
    ]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    gender_probability = models.FloatField()
    age = models.IntegerField()
    
    AGE_GROUPS = [
        ("child", "Child"),
        ("teenager", "Teenager"),
       ( "adult", "Adult"),
       ( "senior", "Senior")
    ]
    age_group = models.CharField(max_length=10, choices=AGE_GROUPS)
    country_id = models.CharField(max_length=2)
    country_name = models.CharField(max_length=100)
    country_probability = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=["gender"]),
            models.Index(fields=["country_id"]),
            models.Index(fields=["age"]),
            models.Index(fields=["age_group"]),
            models.Index(fields=["gender", "country_id"]),
            models.Index(fields=["gender", "age_group"]),
            models.Index(fields=["country_id", "age_group"]),
        ]
    
    def __str__(self):
        return self.name
    