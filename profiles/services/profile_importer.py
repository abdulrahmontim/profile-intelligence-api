import csv
import io
from ..models import Profile

CHUNK_SIZE = 1000
REQUIRED_FIELDS = {"name", "gender", "age", "age_group", "country_id", "country_name"}
VALID_GENDERS = {"male", "female"}
VALID_AGE_GROUPS = {"child", "teenager", "adult", "senior"}


def process_csv(file_buffer) -> dict:
    text_stream = io.TextIOWrapper(file_buffer, encoding="utf-8", errors="replace")
    reader = csv.DictReader(text_stream)

    total_rows = 0
    inserted = 0
    skipped = 0
    reasons = {
        "duplicate_name": 0,
        "invalid_age": 0,
        "invalid_gender": 0,
        "missing_fields": 0,
        "malformed_row": 0,
    }

    chunk = []
    chunk_names = set()

    def insert_chunk(current_chunk, current_names):
        nonlocal inserted, skipped

        if not current_chunk:
            return

        existing_in_db = set(
            Profile.objects.filter(name__in=current_names).values_list("name", flat=True)
        )

        valid_profiles = []
        for profile in current_chunk:
            if profile.name in existing_in_db:
                skipped += 1
                reasons["duplicate_name"] += 1
            else:
                valid_profiles.append(profile)

        if valid_profiles:
            Profile.objects.bulk_create(valid_profiles, ignore_conflicts=True)
            inserted += len(valid_profiles)

    for row in reader:
        total_rows += 1

        try:
            if not row or None in row.values():
                skipped += 1
                reasons["malformed_row"] += 1
                continue

            missing = [f for f in REQUIRED_FIELDS if not str(row.get(f, "")).strip()]
            if missing:
                skipped += 1
                reasons["missing_fields"] += 1
                continue

            name = row["name"].strip().lower()

            if name in chunk_names:
                skipped += 1
                reasons["duplicate_name"] += 1
                continue

            try:
                age = int(row["age"])
                if age < 0:
                    raise ValueError
            except (ValueError, KeyError):
                skipped += 1
                reasons["invalid_age"] += 1
                continue

            gender = row["gender"].strip().lower()
            if gender not in VALID_GENDERS:
                skipped += 1
                reasons["invalid_gender"] += 1
                continue

            age_group = row["age_group"].strip().lower()
            if age_group not in VALID_AGE_GROUPS:
                skipped += 1
                reasons["malformed_row"] += 1
                continue

            chunk_names.add(name)
            chunk.append(Profile(
                name=name,
                gender=gender,
                age=age,
                age_group=age_group,
                country_id=row["country_id"].strip().upper(),
                country_name=row["country_name"].strip(),
                gender_probability=float(row.get("gender_probability") or 0),
                country_probability=float(row.get("country_probability") or 0),
            ))

            if len(chunk) >= CHUNK_SIZE:
                insert_chunk(chunk, chunk_names)
                chunk = []
                chunk_names = set()

        except Exception:
            skipped += 1
            reasons["malformed_row"] += 1
            continue

    if chunk:
        insert_chunk(chunk, chunk_names)

    return {
        "status": "success",
        "total_rows": total_rows,
        "inserted": inserted,
        "skipped": skipped,
        "reasons": {k: v for k, v in reasons.items() if v > 0},
    }