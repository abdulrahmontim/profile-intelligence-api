from django.urls import path
from . import views

urlpatterns = [
    path("users/me", views.MeView.as_view(), name="me"),
]