from django.urls import path
from .views import ProfileListCreateView, ProfileDetailView, ProfileSearchView, ProfileExportView

urlpatterns = [
    path("api/profiles", ProfileListCreateView.as_view(), name="profile_list_create"),
    path("api/profiles/search", ProfileSearchView.as_view(), name="profile_search"),
    path("api/profiles/export", ProfileExportView.as_view(), name="profile_export"),
    path("api/profiles/<uuid:id>", ProfileDetailView.as_view(), name="profile_detail")
]