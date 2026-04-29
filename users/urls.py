from django.urls import path
from . import views

urlpatterns = [
    path("github", views.GithubLoginView.as_view(), name="github_login"),
    path("github/callback", views.GithubCallbackView.as_view(), name="github_callback"),
    path("cli/callback", views.GithubCLICallbackView.as_view(), name="cli_callback"),
    path("refresh", views.GithubRefreshView.as_view(), name="refresh"),
    path("logout", views.GithubLogoutView.as_view(), name="logout")
]
