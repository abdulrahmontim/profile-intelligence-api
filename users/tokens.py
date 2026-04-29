import jwt
import secrets
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from .models import RefreshToken



def issue_access_token(user):
    payload = {
        "user_id": str(user.id),
        "username": user.username,
        "role": user.role,
        "exp": timezone.now() + timedelta(minutes=3)
    }

    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def issue_refresh_token(user):
    refresh_token = secrets.token_urlsafe(64)
    exp = timezone.now() + timedelta(minutes=5)
    RefreshToken.objects.create(
        user=user,
        token=refresh_token,
        expires_at = exp
    )
    
    return refresh_token
    


def issue_token_pair(user):
    return {
        "access_token": issue_access_token(user),
        "refresh_token": issue_refresh_token(user)
    }


def decode_access_token(token):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception("Token expired")
    except jwt.InvalidTokenError:
        raise Exception("Invalid token")
