from django.urls import path
from .views import ProfileListCreateView, ProfileDetailView, ProfileSearchView

urlpatterns = [
    path("api/profiles", ProfileListCreateView.as_view()),
    path("api/profiles/search", ProfileSearchView.as_view()),
    path("api/profiles/<uuid:id>", ProfileDetailView.as_view()),
]