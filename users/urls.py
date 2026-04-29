from django.urls import path
from . import views

urlpatterns = [
    path("github", views.GithubLoginView.as_view(), name="github_login"),
    path("github/callback", views.GithubCallbackView.as_view(), name="github_callback"),
    path("refresh", views.GithubRefreshView.as_view(), name="refresh"),
    path("logout", views.GithubLogoutView.as_view(), name="logout")
]
