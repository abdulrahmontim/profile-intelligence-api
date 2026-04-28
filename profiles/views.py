from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views import View
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from .models import Profile
from .serializers import ProfileSerializer, ProfileListSerializer
from .pagination import ProfilePagination
from .permissions import ReqAPIVersionHeader
from .services.profile_filter import get_profile_filter
from .services.parse_query import get_parse_query
from .services.profile_csv import generate_profile_csv
import requests
from pycountry import countries
from django.http import StreamingHttpResponse


class ProfileBaseView():
    permission_classes = [ReqAPIVersionHeader]
    ...


class ProfileListCreateView(ProfileBaseView, APIView):
    def post(self, request):
        name = request.data.get("name")
        
        if not name:
            return Response({
                "status": "error",
                "message": "Missing or empty name"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not isinstance(name, str):
            return Response({
                "status": "error",
                "message": "Invalid type"
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        name = name.strip().lower()
        
        existing_profile = Profile.objects.filter(name=name).first()
        if existing_profile:
            serializer = ProfileSerializer(existing_profile)
            return Response({
                "status": "success",
                "message": "Profile already exists",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        
        try:
            gender_res = requests.get(f"https://api.genderize.io?name={name}", timeout=10).json()
            age_res = requests.get(f"https://api.agify.io?name={name}", timeout=10).json()
            nationality_res = requests.get(f"https://api.nationalize.io?name={name}", timeout=10).json()

            if not gender_res.get("gender") or gender_res.get("count") == 0:
                return Response({"status": "error",
                                 "message": "Genderize returned an invalid response"},
                                status=status.HTTP_502_BAD_GATEWAY)
            if age_res.get("age") is None:
                return Response({"status": "error",
                                 "message": "Agify returned an invalid response"},
                                status=status.HTTP_502_BAD_GATEWAY)
            if not nationality_res.get("country"):
                return Response({"status": "error",
                                 "message": "Nationalize returned an invalid response"},
                                status=status.HTTP_502_BAD_GATEWAY)

            top_country = None
            highest_prob = 0

            for country in nationality_res["country"]:
                if country['probability'] > highest_prob:
                    highest_prob = country['probability']
                    top_country = country
            
            age_group = None
            profile_age = age_res.get("age")

            if profile_age is not None:
                if 0 <= profile_age <= 12:
                    age_group = "child"
                elif 13 <= profile_age <= 19:
                    age_group = "teenager"
                elif 20 <= profile_age <= 59:
                    age_group = "adult"
                elif profile_age >= 60:
                    age_group = "senior"
            
            country_res = countries.get(alpha_2=top_country["country_id"])
            
            profile = Profile.objects.create(
                name=name,
                gender=gender_res['gender'],
                gender_probability=gender_res['probability'],
                age=age_res['age'],
                age_group=age_group,
                country_id=top_country['country_id'],
                country_name=country_res.name if country_res else None,
                country_probability=top_country['probability']
            )
            
            serializer = ProfileSerializer(profile)
            return Response({
                "status": "success",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)

        except Exception:
            return Response({"status": "error",
                             "message": "Could not reach external API."
                             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
    def get(self, request):
        profiles = get_profile_filter(request)
        
        paginator = ProfilePagination()
        paginated_profiles = paginator.paginate_queryset(profiles, request)
        
        if paginated_profiles is not None:
            serializer = ProfileListSerializer(paginated_profiles, many=True)
            
            return paginator.get_paginated_response(serializer.data)
        
        serializer = ProfileListSerializer(profiles, many=True)
        return Response(serializer.data)


class ProfileDetailView(ProfileBaseView, APIView):
    def get(self, request, id):
        try:
            profile = Profile.objects.get(pk=id)
        except (Profile.DoesNotExist, ValidationError):
            return Response({
            "status": "error",
            "message": "Profile not found"
        }, status=status.HTTP_404_NOT_FOUND)
            
        serializer = ProfileSerializer(profile)
        
        return Response({
            "status": "success", 
            "data": serializer.data
        }, status=status.HTTP_200_OK)
        
    def delete(self, request, id):
        try:
            profile = Profile.objects.get(pk=id)
        except (Profile.DoesNotExist, ValidationError):
            return Response({
            "status": "error",
            "message": "Profile not found"
        }, status=status.HTTP_404_NOT_FOUND)
        
        profile.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)

 
class ProfileSearchView(ProfileBaseView, APIView):
 
    def get(self, request):
        query = request.query_params.get("q")
        
        if not query:
            return Response({
                "status": "error",
                "message": "Invalid query parameters"
            }, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            filters = get_parse_query(query)
            
        except ValueError:
            return Response({
                "status": "error",
                "message": "Unable to interpret query"
            }, status=status.HTTP_400_BAD_REQUEST
            )
        
        profiles = Profile.objects.filter(**filters)
        
        paginator = ProfilePagination()
        paginated_profiles = paginator.paginate_queryset(profiles, request)
        serializer = ProfileListSerializer(paginated_profiles, many=True)
        
        return paginator.get_paginated_response(serializer.data)
    

class ProfileExportView(View):

    def get(self, request):
        format = request.GET.get("format")

        if format != "csv":
            return JsonResponse({
                "status": "error",
                "message": "Only csv format is supported"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            profiles = get_profile_filter(request)
        except ValueError as e:
            return JsonResponse({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        return generate_profile_csv(profiles)
            