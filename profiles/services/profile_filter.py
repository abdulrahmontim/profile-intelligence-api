from ..models import Profile


def get_profile_filter(request):
    profiles = Profile.objects.all()

    gender = request.GET.get("gender")
    country_id = request.GET.get("country_id")
    age_group = request.GET.get("age_group")
    min_age = request.GET.get("min_age")
    max_age = request.GET.get("max_age")
    min_gender_prob = request.GET.get("min_gender_probability")
    min_country_prob = request.GET.get("min_country_probability")
    sort_by = request.GET.get("sort_by")
    order = request.GET.get("order", "asc")

    if gender:
        profiles = profiles.filter(gender__iexact=gender)
    if country_id:
        profiles = profiles.filter(country_id__iexact=country_id)
    if age_group:
        profiles = profiles.filter(age_group__iexact=age_group)

    try:
        if min_age:
            profiles = profiles.filter(age__gte=int(min_age))
        if max_age:
            profiles = profiles.filter(age__lte=int(max_age))
        if min_gender_prob:
            profiles = profiles.filter(gender_probability__gte=float(min_gender_prob))
        if min_country_prob:
            profiles = profiles.filter(country_probability__gte=float(min_country_prob))
    except ValueError:
        raise ValueError("Invalid numeric query parameter")

    order = (order or "asc").lower().strip()
    if order not in ("asc", "desc"):
        raise ValueError("Invalid order parameter")

    sort_fields = {"age", "created_at", "gender_probability"}
    if sort_by and sort_by in sort_fields:
        ordering = f"-{sort_by}" if order == "desc" else sort_by
    else:
        ordering = "-created_at"

    return profiles.order_by(ordering, "id")