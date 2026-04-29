from .tokens import decode_access_token
from .models import User


class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.auth_user = None

        auth_header = request.headers.get("Authorization", "")

        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = decode_access_token(token)
                request.auth_user = User.objects.get(
                    id=payload["user_id"],
                    is_active=True
                )
            except Exception:
                request.auth_user = None

        return self.get_response(request)