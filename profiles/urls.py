from django.urls import path
from . import views


urlpatterns = [
    path("api/profiles", views.create_profile, name="create_profile")
]