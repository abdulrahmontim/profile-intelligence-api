from django.urls import path
from .views import ProfileListCreateView, ProfileDetailView, ProfileSearchView, ProfileExportView, ProfileImportView

urlpatterns = [
    path("profiles", ProfileListCreateView.as_view(), name="profile_list_create"),
    path("profiles/search", ProfileSearchView.as_view(), name="profile_search"),
    path("profiles/export", ProfileExportView.as_view(), name="profile_export"),
    path("profiles/<uuid:id>", ProfileDetailView.as_view(), name="profile_detail"),
    path("profiles/import", ProfileImportView.as_view(), name="profile_import")
]