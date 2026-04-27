from rest_framework.permissions import BasePermission
from rest_framework.exceptions import ValidationError


class ReqAPIVersionHeader(BasePermission):
    ALLOWED_VERSIONS = {"1"}
    
    def has_permission(self, request, view):
        version = request.headers.get("X-API-Version")
        
        if not version:
            raise ValidationError({
                "status": "error",
                "message": "API version header is required"
            })
            
        if version not in self.ALLOWED_VERSIONS:
            raise ValidationError({
                "status": "error",
                "message": "Unsupported API version"
            })
            
        return True