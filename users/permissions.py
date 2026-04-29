from functools import wraps
from django.http import JsonResponse



def require_auth(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not getattr(request, "auth_user", None):
            return JsonResponse(
                {"status": "error", "message": "authentication required"},
                status=401
            )
        if not request.auth_user.is_active:
            return JsonResponse(
                {"status": "error", "message": "account inactive"},
                status=403
            )
        return view_func(request, *args, **kwargs)
    return wrapper




def require_role(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not getattr(request, "auth_user", None):
                return JsonResponse(
                    {"status": "error", "message": "authentication required"},
                    status=401
                )
            if not request.auth_user.is_active:
                return JsonResponse(
                    {"status": "error", "message": "Account inactive"},
                    status=403
                )
            if request.auth_user.role not in roles:
                return JsonResponse(
                    {"status": "error", "message": "permission denied"},
                    status=403
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


require_admin = require_role("admin")
require_analyst_or_admin = require_role("admin", "analyst")