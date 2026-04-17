from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Profile
from.serializers import ProfileSerializer
import requests


class ProfileListCreateView(APIView):
    def post(self, request):
        name = request.data.get("name", "").lower()
        
        if not name:
            return Response({
                "status": "error",
                "message": "Missing name"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        existing_profile = Profile.objects.filter(name=name).first()
        if existing_profile:
            serializer = ProfileSerializer(existing_profile)
            return Response({
                "status": "success",
                "message": "Profile already exists",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        
        try:
            gender_res = requests.get(f"https://api.genderize.io?name={name}").json()
            age_res = requests.get(f"https://api.agify.io?name={name}").json()
            nationality_res = requests.get(f"https://api.nationalize.io?name={name}").json()

            if not gender_res.get("gender") or gender_res.get("count") == 0:
                return Response({"status": "502",
                                 "message": "Genderize returned an invalid response"},
                                status=status.HTTP_502_BAD_GATEWAY)
            if age_res.get("age") is None:
                return Response({"status": "502",
                                 "message": "Agify returned an invalid response"},
                                status=status.HTTP_502_BAD_GATEWAY)
            if not nationality_res.get("country"):
                return Response({"status": "502",
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
        return Response({"status": "testing"})

    
