from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from uuid6 import uuid7


class UserManager(BaseUserManager):
    def create_user(self, github_id, username, **extra_fields):
        user = self.model(github_id=github_id, username=username, **extra_fields)
        user.set_unusable_password()
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    github_id = models.CharField(max_length=255, unique=True)
    username = models.CharField(max_length=255, unique=True)
    email = models.EmailField(blank=True)
    avatar_url = models.URLField(max_length=500, null=True, blank=True)
    
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("analyst", "Analyst")
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="analyst")
    is_active = models.BooleanField(default=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = "github_id"
    REQUIRED_FIELDS = []
    
    
    def __str__(self):
        return self.username


class RefreshToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=512, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    valid = models.BooleanField(default=True)