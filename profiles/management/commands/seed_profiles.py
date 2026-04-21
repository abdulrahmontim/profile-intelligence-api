import json
from django.core.management.base import BaseCommand
from profiles.models import Profile

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        file_path = "seed_profiles.json"
        
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)["profiles"]
                
            for item in data:
                Profile.objects.update_or_create(
                    name=item["name"],
                    defaults={
                        "gender": item["gender"],
                        "gender_probability": item["gender_probability"],
                        "age": item["age"],
                        "age_group": item["age_group"],
                        "country_id": item["country_id"],
                        "country_name": item["country_name"],
                        "country_probability": item["country_probability"]
                    }
                )
            self.stdout.write(self.style.SUCCESS("Completed!"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {str(e)}"))