from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import User
import requests


class GithubLoginView(APIView):
    
    def get(self, request):
        ...


class GithubCallbackView(APIView):
    
    def post(self, request):
        ...


class GithubRefreshView(APIView):
    
    def post(self, request):
        ...
        

class GithubLogoutView(APIView):
    
    def post(self, request):
        ...