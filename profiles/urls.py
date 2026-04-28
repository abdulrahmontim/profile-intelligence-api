from django.urls import path
from .views import ProfileListCreateView, ProfileDetailView, ProfileSearchView, ProfileExportView

urlpatterns = [
    path("profiles", ProfileListCreateView.as_view(), name="profile_list_create"),
    path("profiles/search", ProfileSearchView.as_view(), name="profile_search"),
    path("profiles/export", ProfileExportView.as_view(), name="profile_export"),
    path("profiles/<uuid:id>", ProfileDetailView.as_view(), name="profile_detail")
]