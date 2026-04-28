import re


def get_parse_query(query):
    query = query.lower().strip()
    if not query:
        raise ValueError()
    
    filters = {}
    matched = False
    
    has_male = bool(re.search(r"\b(male|males)\b", query))
    has_female = bool(re.search(r"\b(female|females)\b", query))
    
    if has_male and not has_female:
        filters["gender"] = "male"
        matched = True
    elif has_female and not has_male:
        filters["gender"] = "female"
        matched = True
    elif has_male and has_female:
        matched = True
    
    if re.search(r"\b(teenager|teenagers)\b", query):
        filters["age_group"] = "teenager"
        matched = True
    if re.search(r"\b(child|children)\b", query):
        filters["age_group"] = "child"
        matched = True
    if re.search(r"\b(adult|adults)\b", query):
        filters["age_group"] = "adult"
        matched = True
    if re.search(r"\b(senior|seniors)\b", query):
        filters["age_group"] = "senior"
        matched = True
    
    if re.search(r"\byoung\b", query):
        filters["age__gte"] = 16
        filters["age__lte"] = 24
        matched = True
    
    above_match = re.search(r"above (\d+)", query)
    if above_match:
        filters["age__gt"] = int(above_match.group(1))
        matched = True

    below_match = re.search(r"below (\d+)", query)
    if below_match:
        filters["age__lt"] = int(below_match.group(1))
        matched = True

    country_match = re.search(r"from ([a-z ]+)", query)
    if country_match:
        country = country_match.group(1).strip()
        filters["country_name__iexact"] = country
        matched = True


    if not matched:
        raise ValueError("Unable to intepret query")
    
    return filters