from django.urls import path, re_path
from .views import ProfileListCreateView, ProfileDetailView

urlpatterns = [
    # Using re_path allows the slash to be optional (?)
    re_path(r'^api/profiles/?$', ProfileListCreateView.as_view()),
    re_path(r'^api/profiles/(?P<id>[^/]+)/?$', ProfileDetailView.as_view()),
]