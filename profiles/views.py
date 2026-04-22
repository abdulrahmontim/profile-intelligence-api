from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError
from .models import Profile
from .serializers import ProfileSerializer, ProfileListSerializer
from .pagination import ProfilePagination
from .services import parse_query
import requests


class ProfileListCreateView(APIView):
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
                    
            profile = Profile.objects.create(
                name=name,
                gender=gender_res['gender'],
                gender_probability=gender_res['probability'],
                sample_size=gender_res['count'],
                age=age_res['age'],
                age_group=age_group,
                country_id=top_country['country_id'],
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
        profiles = Profile.objects.all()

        gender = request.query_params.get("gender")
        country_id = request.query_params.get("country_id")
        age_group = request.query_params.get("age_group")
        min_age = request.query_params.get("min_age")
        max_age = request.query_params.get("max_age")
        min_gender_prob = request.query_params.get("min_gender_probability")
        min_country_prob = request.query_params.get("min_country_probability")
        sort_by = request.query_params.get("sort_by")
        order = request.query_params.get("order", "asc")
        
        
        if gender:
                profiles = profiles.filter(gender__iexact=gender)
        if country_id:
                profiles = profiles.filter(country_id__iexact=country_id)
        if age_group:
                profiles = profiles.filter(age_group__iexact=age_group)
                
        try:
            if min_age:
                    profiles = profiles.filter(age__gte=int(min_age))
            if max_age:
                    profiles = profiles.filter(age__lte=int(max_age))
            if min_gender_prob:
                    profiles = profiles.filter(gender_probability__gte=float(min_gender_prob))
            if min_country_prob:
                    profiles = profiles.filter(country_probability__gte=float(min_country_prob))

        except ValueError:
            return Response({"status": "error",
                             "message": "Invalid query parameters"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        
        sort_fields = ["age", "created_at", "gender_probability"]
        if sort_by in sort_fields:
            if order == "desc":
                sort_by = f"-{sort_by}"
            
            profiles =  profiles.order_by(sort_by)
        
        paginator = ProfilePagination()
        paginated_profiles = paginator.paginate_queryset(profiles, request)
        
        if paginated_profiles is not None:
            serializer = ProfileListSerializer(paginated_profiles, many=True)
            
            return paginator.get_paginated_response(serializer.data)
        
        serializer = ProfileSerializer(paginated_profiles, many=True)
        return Response(serializer.data)


class ProfileDetailView(APIView):
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
    
from django.http import HttpResponse
class ProfileSearchView(APIView):
    
    def get(self, request):
        query = request.query_params.get("q")
        
        if not query:
            return Response({
                "status": "error",
                "message": "Invalid query parameters"
            }, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            filters = parse_query(query)
            
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