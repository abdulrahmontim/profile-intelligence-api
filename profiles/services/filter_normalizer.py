import json
import hashlib



def normalize_filters(params: dict):
    cleaned_filter = {}
    
    if params.get("gender"):
        cleaned_filter["gender"] = params["gender"].lower().strip()
        
    if params.get("country_id"):
        cleaned_filter["country_id"] = params["country_id"].upper().strip()
        
    if params.get("age_group"):
        cleaned_filter["age_group"] = params["age_group"].lower().strip()

    if params.get("min_age"):
        try:
            cleaned_filter["min_age"] = int(params["min_age"])
        except ValueError:
            ...

    if params.get("max_age"):
        try:
            cleaned_filter["max_age"] = int(params["max_age"])
        except ValueError:
            ...

    if params.get("min_gender_probability"):
        try:
            cleaned_filter["min_gender_probability"] = float(params["min_gender_probability"])
        except ValueError:
            pass

    if params.get("min_country_probability"):
        try:
            cleaned_filter["min_country_probability"] = float(params["min_country_probability"])
        except ValueError:
            ...

    sort_fields = {"age", "created_at", "gender_probability"}
    if params.get("sort_by") and params["sort_by"] in sort_fields:
        cleaned_filter["sort_by"] = params["sort_by"].lower().strip()
        cleaned_filter["order"] = (params.get("order") or "asc").lower().strip()

    cleaned_filter["page"] = int(params.get("page", 1))
    cleaned_filter["limit"] = int(params.get("limit", 10))

    return cleaned_filter


def normalize_search_filters(filters: dict):
    cleaned_filter = {}

    for key, value in filters.items():
        if isinstance(value, str):
            cleaned_filter[key] = value.lower().strip()
        elif isinstance(value, int):
            cleaned_filter[key] = value
        elif isinstance(value, float):
            cleaned_filter[key] = round(value, 2)
        else:
            cleaned_filter[key] = value

    return dict(sorted(cleaned_filter.items()))


def make_cache_key(prefix: str, filters: dict):
    serialized = json.dumps(filters, sort_keys=True)
    hash_val = hashlib.md5(serialized.encode()).hexdigest()
    return f"{prefix}:{hash_val}"


