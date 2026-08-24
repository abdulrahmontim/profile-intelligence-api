import csv
import io
import uuid as uuidlib

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Profile
from .services.filter_normalizer import (
    make_cache_key,
    normalize_filters,
    normalize_search_filters,
)
from .services.parse_query import get_parse_query
from .services.profile_importer import process_csv
from users.models import User
from users.tokens import issue_access_token

CSV_HEADERS = (
    "name", "gender", "age", "age_group",
    "country_id", "country_name",
    "gender_probability", "country_probability",
)

ROW = {
    "name": "ada lovelace",
    "gender": "female",
    "age": 36,
    "age_group": "adult",
    "country_id": "NG",
    "country_name": "Nigeria",
    "gender_probability": 0.98,
    "country_probability": 0.91,
}


def make_profile(name, gender="female", age=30, age_group="adult",
                 country_id="NG", country_name="Nigeria",
                 gender_probability=0.95, country_probability=0.9):
    return Profile(
        name=name,
        gender=gender,
        age=age,
        age_group=age_group,
        country_id=country_id,
        country_name=country_name,
        gender_probability=gender_probability,
        country_probability=country_probability,
    )


def uploaded(rows, filename="bulk.csv"):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(CSV_HEADERS))
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return SimpleUploadedFile(filename, buf.getvalue().encode(), content_type="text/csv")


class ParseQueryTests(TestCase):
    def test_male_keyword_maps_to_gender_filter(self):
        self.assertEqual(get_parse_query("list all males"), {"gender": "male"})

    def test_female_with_age_and_country(self):
        filters = get_parse_query("females above 30 from Nigeria")
        self.assertEqual(filters["gender"], "female")
        self.assertEqual(filters["age__gt"], 30)
        self.assertEqual(filters["country_name__iexact"], "nigeria")

    def test_young_adults_maps_to_age_range(self):
        self.assertEqual(
            get_parse_query("young adults"),
            {"age_group": "adult", "age__gte": 16, "age__lte": 24},
        )

    def test_children_below_age(self):
        filters = get_parse_query("children below 10")
        self.assertEqual(filters["age_group"], "child")
        self.assertEqual(filters["age__lt"], 10)

    def test_unrecognized_query_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_parse_query("purple monkey dishwasher")

    def test_blank_query_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_parse_query("   ")


class FilterNormalizerTests(TestCase):
    def test_cache_key_is_independent_of_dict_order(self):
        first = make_cache_key("profiles:list", {"gender": "male", "age": 20})
        second = make_cache_key("profiles:list", {"age": 20, "gender": "male"})
        self.assertEqual(first, second)

    def test_cache_key_changes_with_values(self):
        self.assertNotEqual(
            make_cache_key("profiles:list", {"gender": "male"}),
            make_cache_key("profiles:list", {"gender": "female"}),
        )

    def test_normalize_filters_coerces_types_and_drops_garbage(self):
        cleaned = normalize_filters({
            "gender": " FEMALE ",
            "min_age": "25",
            "max_age": "abc",
            "sort_by": "age",
            "order": "DESC",
        })
        self.assertEqual(cleaned["gender"], "female")
        self.assertEqual(cleaned["min_age"], 25)
        self.assertNotIn("max_age", cleaned)
        self.assertEqual(cleaned["sort_by"], "age")
        self.assertEqual(cleaned["order"], "desc")
        self.assertEqual(cleaned["limit"], 10)
        self.assertEqual(cleaned["page"], 1)

    def test_normalize_search_filters_sorts_and_cleans(self):
        cleaned = normalize_search_filters({"z": 1, "a": " X ", "m": 2.345})
        self.assertEqual(list(cleaned.keys()), ["a", "m", "z"])
        self.assertEqual(cleaned["a"], "x")
        self.assertEqual(cleaned["m"], round(2.345, 2))


class ImporterTests(TestCase):
    def test_inserts_valid_rows(self):
        result = process_csv(uploaded([dict(ROW), dict(ROW, name="grace hopper", age=45)]))
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["total_rows"], 2)
        self.assertEqual(result["inserted"], 2)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(Profile.objects.count(), 2)

    def test_skips_duplicate_names_within_file(self):
        result = process_csv(uploaded([
            dict(ROW),
            dict(ROW),
            dict(ROW, name="grace hopper"),
        ]))
        self.assertEqual(result["inserted"], 2)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["reasons"]["duplicate_name"], 1)

    def test_skips_names_already_in_database(self):
        make_profile(name="ada lovelace").save()
        result = process_csv(uploaded([
            dict(ROW),
            dict(ROW, name="new person"),
        ]))
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["reasons"]["duplicate_name"], 1)
        self.assertEqual(Profile.objects.count(), 2)

    def test_reports_reasons_for_invalid_rows(self):
        result = process_csv(uploaded([
            dict(ROW),
            dict(ROW, name="bad age", age="notanumber"),
            dict(ROW, name="negative age", age=-3),
            dict(ROW, name="bad gender", gender="unknown"),
            {**ROW, "name": ""},
        ]))
        self.assertEqual(result["total_rows"], 5)
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(result["skipped"], 4)
        reasons = result["reasons"]
        self.assertGreaterEqual(reasons.get("invalid_age", 0), 2)
        self.assertGreaterEqual(reasons.get("invalid_gender", 0), 1)
        self.assertGreaterEqual(reasons.get("missing_fields", 0), 1)


class ProfileApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.admin = User.objects.create(
            github_id="400001", username="admin-user", role="admin"
        )
        self.analyst = User.objects.create(
            github_id="400002", username="analyst-user", role="analyst"
        )
        Profile.objects.bulk_create([
            make_profile("ada lovelace", age=36),
            make_profile("grace hopper", age=45),
            make_profile("alan turing", gender="male", age=41,
                         country_id="GB", country_name="United Kingdom"),
        ])

    def auth_as(self, user, version=None):
        credentials = {}
        if user is not None:
            credentials["HTTP_AUTHORIZATION"] = f"Bearer {issue_access_token(user)}"
        if version is not None:
            credentials["HTTP_X_API_VERSION"] = version
        self.client.credentials(**credentials)

    def test_list_requires_authentication(self):
        self.auth_as(None, version="1")
        res = self.client.get("/api/profiles")
        self.assertEqual(res.status_code, 401)

    def test_list_rejects_missing_version_header_even_when_authenticated(self):
        self.auth_as(self.analyst, version=None)
        res = self.client.get("/api/profiles")
        self.assertEqual(res.status_code, 400)

    def test_list_filters_by_gender(self):
        self.auth_as(self.analyst, version="1")
        res = self.client.get("/api/profiles?gender=female")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["total"], 2)
        self.assertTrue(all(p["gender"] == "female" for p in body["data"]))

    def test_list_supports_sorting_by_age_descending(self):
        self.auth_as(self.analyst, version="1")
        res = self.client.get("/api/profiles?sort_by=age&order=desc&limit=10")
        body = res.json()
        names = [p["name"] for p in body["data"]]
        self.assertEqual(names[0], "grace hopper")
        self.assertEqual(names[-1], "ada lovelace")

    def test_search_parses_natural_language_query(self):
        self.auth_as(self.analyst, version="1")
        res = self.client.get("/api/profiles/search?q=males%20from%20united%20kingdom")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["data"][0]["name"], "alan turing")

    def test_search_returns_400_for_uninterpretable_query(self):
        self.auth_as(self.analyst, version="1")
        res = self.client.get("/api/profiles/search?q=banana%20phone")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["message"], "Unable to interpret query")

    def test_detail_unknown_uuid_returns_404(self):
        self.auth_as(self.analyst, version="1")
        missing = uuidlib.uuid4()
        res = self.client.get(f"/api/profiles/{missing}")
        self.assertEqual(res.status_code, 404)

    def test_export_rejects_non_csv_format(self):
        self.auth_as(self.analyst, version="1")
        res = self.client.get("/api/profiles/export?format=json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["message"], "Only csv format is supported")

    def test_export_streams_csv_with_data(self):
        self.auth_as(self.analyst, version="1")
        res = self.client.get("/api/profiles/export?format=csv")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res["Content-Type"])
        content = b"".join(res.streaming_content).decode()
        self.assertIn("name", content.splitlines()[0])
        self.assertIn("ada lovelace", content)

    def test_import_is_admin_only(self):
        self.auth_as(self.analyst, version="1")
        res = self.client.post("/api/profiles/import",
                               {"file": uploaded([dict(ROW)])}, format="multipart")
        self.assertEqual(res.status_code, 403)

    def test_import_ingests_file_for_admin(self):
        self.auth_as(self.admin, version="1")
        res = self.client.post("/api/profiles/import", {
            "file": uploaded([
                dict(ROW, name="katherine johnson"),
                dict(ROW, name="katherine johnson"),
                dict(ROW, name="bad age", age="oops"),
            ]),
        }, format="multipart")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["inserted"], 1)
        self.assertEqual(body["skipped"], 2)
        self.assertEqual(Profile.objects.count(), 4)

    def test_import_rejects_non_csv_files(self):
        self.auth_as(self.admin, version="1")
        bogus = SimpleUploadedFile("data.txt", b"name\nx\n", content_type="text/plain")
        res = self.client.post("/api/profiles/import", {"file": bogus},
                               format="multipart")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["message"], "Only CSV files are supported")

    def test_create_endpoint_is_forbidden_for_analysts(self):
        self.auth_as(self.analyst, version="1")
        res = self.client.post("/api/profiles", {"name": "new profile"}, format="json")
        self.assertEqual(res.status_code, 403)
