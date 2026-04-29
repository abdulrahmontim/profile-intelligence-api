from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.utils import timezone
from .models import User, RefreshToken
from django.shortcuts import redirect
from urllib.parse import urlencode
from .pkce import generate_code_challenge, generate_code_verifier, generate_state
from .tokens import issue_token_pair
import httpx


class GithubLoginView(APIView):
    
    def get(self, request):
        code_verifier = generate_code_verifier()
        code_challenge = generate_code_challenge(code_verifier)
        state = generate_state()
        
        request.session["code_verifier"] = code_verifier
        request.session["oauth_state"] = state
        
        params = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": settings.GITHUB_REDIRECT_URI,
            "scope": "read:user user:email",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }

        return redirect(f"https://github.com/login/oauth/authorize?{urlencode(params)}")

class GithubCallbackView(APIView):
    
    def get(self, request):
        code = request.GET.get("code")
        state = request.GET.get("state")
        code_verifier = request.session.get("code_verifier")
        
        if state != request.session.get("oauth_state"):
            return Response({
                "status": "error",
                "message": "state mismatch"
            }, status=status.HTTP_400_BAD_REQUEST)

        request.session.pop("code_verifier", None)
        request.session.pop("oauth_state", None)
        
        token_res = httpx.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "code_verifier": code_verifier,
                "redirect_uri": settings.GITHUB_REDIRECT_URI,
            },
            headers={"Accept": "application/json"},
        )
        
        github_token = token_res.json().get("access_token")
        
        user_res = httpx.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {github_token}"},
        )
        
        github_user = user_res.json()
        
        user, created = User.objects.update_or_create(
            github_id=str(github_user["id"]),
            defaults={
                "username": github_user["login"],
                "email": github_user.get("email") or "",
                "avatar_url": github_user.get("avatar_url") or "",
            }
        )
        user.last_login_at = timezone.now()
        user.save(update_fields=["last_login_at"])
        
        tokens = issue_token_pair(user)
        
        return Response({
            "status": "success",
            **tokens
        })
        

class GithubCLICallbackView(APIView):

    def post(self, request):
        code = request.data.get("code")
        code_verifier = request.data.get("code_verifier")
        redirect_uri = request.data.get("redirect_uri")

        if not code or not code_verifier:
            return Response({"status": "error", "message": "Missing code or verifier"},
                            status=status.HTTP_400_BAD_REQUEST)

        token_res = httpx.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "code_verifier": code_verifier,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )

        github_token = token_res.json().get("access_token")
        if not github_token:
            return Response({"status": "error", "message": "Failed to exchange code"},
                            status=status.HTTP_400_BAD_REQUEST)

        user_res = httpx.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {github_token}"},
        )
        github_user = user_res.json()

        user, created = User.objects.update_or_create(
            github_id=str(github_user["id"]),
            defaults={
                "username": github_user["login"],
                "email": github_user.get("email") or "",
                "avatar_url": github_user.get("avatar_url") or "",
            }
        )
        user.last_login_at = timezone.now()
        user.save(update_fields=["last_login_at"])

        tokens = issue_token_pair(user)

        return Response({
            "status": "success",
            "username": user.username,
            "role": user.role,
            **tokens
        })


class GithubRefreshView(APIView):
    
    def post(self, request):
        refresh_token = request.data.get("refresh_token")
        if not refresh_token:
            return Response({
                "status": "error",
                "message": "refresh token is required"
            })
        try:
            ref_token = RefreshToken.objects.get(token=refresh_token, valid=True)
        except RefreshToken.DoesNotExist:
            return Response({
                "status": "error", 
                "message": "invalid token"
            })
            
        if ref_token.expires_at < timezone.now():
            ref_token.valid = False
            ref_token.save()
            return Response({
                "status": "error",
                "message": "Refresh token expired"
                }, status=status.HTTP_401_UNAUTHORIZED)

        ref_token.valid = False
        ref_token.save()

        tokens = issue_token_pair(ref_token.user)
        return Response({"status": "success", **tokens})



class GithubLogoutView(APIView):
    
    def post(self, request):
        refresh_token = request.data.get("refresh_token")
        
        try:
            ref_token = RefreshToken.objects.get(token=refresh_token, valid=True)
            
        except RefreshToken.DoesNotExist:
            return Response({
                "status": "error",
                "message": "invalid token"
            })
        
        ref_token.valid = False
        ref_token.save()
        
        return Response({
            "status": "success", 
            "message": "logged out"
        })