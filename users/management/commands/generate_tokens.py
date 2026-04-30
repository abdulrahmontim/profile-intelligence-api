import warnings
warnings.filterwarnings("ignore")

from django.core.management.base import BaseCommand
from users.models import User
from users.tokens import issue_token_pair


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        admin, _ = User.objects.get_or_create(
            github_id="test_admin_001",
            defaults={
                "username": "admin_test_user",
                "email": "admin@test.com",
                "role": "admin",
                "is_active": True,
            }
        )
        admin.role = "admin"
        admin.save()

        analyst, _ = User.objects.get_or_create(
            github_id="test_analyst_001",
            defaults={
                "username": "analyst_test_user",
                "email": "analyst@test.com",
                "role": "analyst",
                "is_active": True,
            }
        )

        a = issue_token_pair(admin)
        b = issue_token_pair(analyst)

        self.stdout.write("ADMIN ACCESS: " + a["access_token"])
        self.stdout.write("ADMIN REFRESH: " + a["refresh_token"])
        self.stdout.write("ANALYST ACCESS: " + b["access_token"])