from django.urls import path
from . import views


urlpatterns = [
    path("api/profiles/", views.ProfileListCreateView.as_view(), name="profile-list-create"),
    path("api/profiles/<uuid:id>", views.ProfileDetailView.as_view(), name="profile-detail")
]