from django.http import StreamingHttpResponse
from django.utils import timezone
import csv


CSV_HEADERS = [
    "id", "name", "gender", "gender_probability",
    "age", "age_group", "country_id", "country_name",
    "country_probability", "created_at",
]

class Echo:
    def write(self, value):
        return value

def generate_profile_csv(profiles):
    writer    = csv.writer(Echo())
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")

    def row_generator():
        yield writer.writerow(CSV_HEADERS)
        for p in profiles.iterator():
            yield writer.writerow([
                p.id,
                p.name,
                p.gender,
                round(p.gender_probability, 2),
                p.age,
                p.age_group,
                p.country_id,
                p.country_name or "",
                round(p.country_probability, 2),
                p.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ])

    response = StreamingHttpResponse(row_generator(), content_type="text/csv", status=200)
    response["Content-Disposition"] = f'attachment; filename="profiles_{timestamp}.csv"'
    return response