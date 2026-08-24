import base64
import hashlib
from datetime import timedelta

import jwt
from django.conf import settings
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import RefreshToken, User
from .pkce import generate_code_challenge, generate_code_verifier, generate_state
from .tokens import decode_access_token, issue_access_token, issue_refresh_token


def create_user(**kwargs):
    defaults = {
        "github_id": "100001",
        "username": "octocat",
        "email": "octo@example.com",
        "role": "analyst",
        "is_active": True,
    }
    defaults.update(kwargs)
    return User.objects.create(**defaults)


class PkceTests(TestCase):
    def test_code_verifier_meets_rfc7636_minimum_length(self):
        verifier = generate_code_verifier()
        self.assertGreaterEqual(len(verifier), 43)

    def test_code_challenge_is_urlsafe_s256_of_verifier(self):
        verifier = "a" * 64
        digest = hashlib.sha256(verifier.encode()).digest()
        expected = base64.urlsafe_b64encode(digest).decode().rstrip("=")
        challenge = generate_code_challenge(verifier)
        self.assertEqual(challenge, expected)
        self.assertNotIn("=", challenge)
        self.assertNotIn("+", challenge)
        self.assertNotIn("/", challenge)

    def test_state_is_unique_per_call(self):
        self.assertNotEqual(generate_state(), generate_state())


class AccessTokenTests(TestCase):
    def setUp(self):
        self.user = create_user()

    def test_issued_token_decodes_to_expected_payload(self):
        token = issue_access_token(self.user)
        payload = decode_access_token(token)
        self.assertEqual(payload["user_id"], str(self.user.id))
        self.assertEqual(payload["username"], "octocat")
        self.assertEqual(payload["role"], "analyst")

    def test_expired_token_is_rejected(self):
        payload = {
            "user_id": str(self.user.id),
            "username": self.user.username,
            "role": self.user.role,
            "exp": timezone.now() - timedelta(minutes=1),
        }
        expired = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
        with self.assertRaisesRegex(Exception, "expired"):
            decode_access_token(expired)

    def test_tampered_token_is_rejected(self):
        with self.assertRaises(Exception):
            decode_access_token("not-a-real-jwt")


class RefreshTokenTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.client = APIClient()

    def _post_refresh(self, payload, ip):
        return self.client.post("/auth/refresh", payload, format="json", REMOTE_ADDR=ip)

    def test_refresh_token_is_persisted_and_valid(self):
        token = issue_refresh_token(self.user)
        stored = RefreshToken.objects.get(token=token)
        self.assertTrue(stored.valid)
        self.assertGreater(stored.expires_at, timezone.now())

    def test_refresh_rotation_issues_new_pair_and_retires_old(self):
        old = issue_refresh_token(self.user)
        res = self._post_refresh({"refresh_token": old}, "10.1.0.1")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["status"], "success")
        self.assertIn("access_token", body)
        self.assertIn("refresh_token", body)
        self.assertNotEqual(body["refresh_token"], old)
        self.assertFalse(RefreshToken.objects.get(token=old).valid)

    def test_used_refresh_token_cannot_be_replayed(self):
        old = issue_refresh_token(self.user)
        self._post_refresh({"refresh_token": old}, "10.2.0.1")
        res = self._post_refresh({"refresh_token": old}, "10.2.0.2")
        self.assertEqual(res.json()["message"], "invalid token")

    def test_missing_refresh_token_returns_error_message(self):
        res = self._post_refresh({}, "10.3.0.1")
        self.assertEqual(res.json()["message"], "refresh token is required")

    def test_expired_refresh_token_returns_401_and_is_retired(self):
        RefreshToken.objects.create(
            user=self.user,
            token="stale-token",
            expires_at=timezone.now() - timedelta(hours=1),
        )
        res = self._post_refresh({"refresh_token": "stale-token"}, "10.3.1.1")
        self.assertEqual(res.status_code, 401)
        self.assertFalse(RefreshToken.objects.get(token="stale-token").valid)

    def test_logout_invalidates_refresh_token(self):
        token = issue_refresh_token(self.user)
        res = self.client.post(
            "/auth/logout",
            {"refresh_token": token},
            format="json",
            REMOTE_ADDR="10.4.0.1",
        )
        self.assertEqual(res.json()["status"], "success")
        self.assertFalse(RefreshToken.objects.get(token=token).valid)


class GithubCallbackBackdoorTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @override_settings(DEBUG=True)
    def test_test_code_yields_admin_tokens_in_debug(self):
        res = self.client.get(
            "/auth/github/callback?code=test_code", REMOTE_ADDR="10.5.0.1"
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["role"], "admin")
        self.assertIn("access_token", body)

        second = self.client.get(
            "/auth/github/callback?code=test_code", REMOTE_ADDR="10.5.0.2"
        )
        self.assertEqual(second.json()["username"], body["username"])
        self.assertEqual(User.objects.filter(username="admin_test_user").count(), 1)

    @override_settings(DEBUG=False)
    def test_test_code_returns_404_when_debug_disabled(self):
        res = self.client.get(
            "/auth/github/callback?code=test_code", REMOTE_ADDR="10.5.0.3"
        )
        self.assertEqual(res.status_code, 404)


class MeEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_user(github_id="200002", username="me-user")

    def test_requires_authentication(self):
        res = self.client.get("/api/users/me")
        self.assertEqual(res.status_code, 401)

    def test_bearer_token_returns_profile(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_access_token(self.user)}")
        res = self.client.get("/api/users/me")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["data"]["username"], "me-user")

    def test_inactive_user_token_is_rejected(self):
        inactive = create_user(github_id="300003", username="ghost", is_active=False)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_access_token(inactive)}")
        res = self.client.get("/api/users/me")
        self.assertEqual(res.status_code, 401)
