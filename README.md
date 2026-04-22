# Profile Intelligence API

A RESTful API for retrieving and analyzing user profile intelligence data.

## 🚀 Live API

**Deployed:** https://profile-intelligence-api.up.railway.app

## Features

- **Profile Intelligence Analysis**: Automatically analyze names to predict gender, age, and nationality.
- **Natural Language Query Engine**: Search profiles using plain English (e.g., "young males from nigeria").
- **Advanced Filtering**: Filter profiles by demographic groups, precise age ranges, and exact probability thresholds.
- **Sorting & Pagination**: Fully paginated responses with customizable sorting parameters.
- **Idempotent Operations**: Prevent duplicate profiles - same name returns existing data.
- **RESTful API**: Clean, standardized API endpoints following REST principles.
- **Real-time Data**: Fetch live intelligence data from external APIs (Genderize, Agify, Nationalize).
- **UUID7 Primary Keys**: Time-ordered unique identifiers for better database performance.
- **Comprehensive Error Handling**: Detailed error responses for API failures and invalid requests.

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/abdulrahmontim/profile-intelligence-api.git
    cd profile-intelligence-api
    ```

2. Create and activate virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4. Run migrations and seed data:
    ```bash
    python manage.py migrate
    python manage.py seed_profiles
    ```

5. Start the development server:
    ```bash
    python manage.py runserver
    ```

## Usage

**Local Development:** http://localhost:8000

---

## API Endpoints

### 1. Create Profile
**POST** `/api/profiles/`

**Request Body:**
```json
{
  "name": "ella"
}
```

**Success Response (201):**
```json
{
  "status": "success",
  "data": {
    "id": "b3f9c1e2-7d4a-4c91-9c2a-1f0a8e5b6d12",
    "name": "ella",
    "gender": "female",
    "gender_probability": 0.99,
    "sample_size": 1234,
    "age": 46,
    "age_group": "adult",
    "country_id": "CD",
    "country_probability": 0.85,
    "created_at": "2026-04-01T12:00:00Z"
  }
}
```

### 2. Get Profile by ID
**GET** `/api/profiles/{id}/`

**Success Response (200):**
```json
{
  "status": "success",
  "data": {
    "id": "b3f9c1e2-7d4a-4c91-9c2a-1f0a8e5b6d12",
    "name": "emmanuel",
    "gender": "male",
    "gender_probability": 0.99,
    "sample_size": 1234,
    "age": 25,
    "age_group": "adult",
    "country_id": "NG",
    "country_probability": 0.85,
    "created_at": "2026-04-01T12:00:00Z"
  }
}
```

### 3. List Profiles
**GET** `/api/profiles/`

**Optional Query Parameters:**
- **String Filters:** `gender`, `country_id`, `age_group`
- **Numeric Filters:** `min_age`, `max_age`, `min_gender_probability`, `min_country_probability`
- **Sorting:** `sort_by` (`age`, `created_at`, `gender_probability`), `order` (`asc`, `desc`)
- **Pagination:** `page` (default: 1), `limit` (max: 50)

**Example:** `/api/profiles/?gender=male&min_age=25&sort_by=age&order=desc`

**Success Response (200):**
```json
{
  "status": "success",
  "page": 1,
  "limit": 10,
  "total": 452,
  "data": [
    {
      "id": "id-1",
      "name": "emmanuel",
      "gender": "male",
      "age": 25,
      "age_group": "adult",
      "country_id": "NG"
    }
  ]
}
```

### 4. Search Profiles (Natural Language)
**GET** `/api/profiles/search`

**Query Parameters:**
- `q` (Required) - Plain text search query.

**Example:** `/api/profiles/search?q=young males from nigeria`

**Success Response (200):** Returns the same paginated structure as the List endpoint.

### 5. Delete Profile
**DELETE** `/api/profiles/{id}/`

**Success Response:** `204 No Content`

---

## Natural Language Query (NLQ)

This API features a custom-built, rule-based Lexical Parser that translates plain English strings into precise database lookups.
the NLP logic is separated from the API routing. `views.py`  extracts the query parameter and passes it to `services.py` file.

**2. The Rule-Based Lexical Parser**
To meet constraints without relying on external LLMs, the parser uses Python's `re` (Regex) module. It scans the lowercase string for specific keyword boundaries (`\b`) and maps them to Django ORM lookups.
- **Demographics:** Translates keywords like "teenager" or "senior" directly into `age_group` filters.
- **Numeric Thresholds:** Captures phrases like "above 30" or "below 18" and dynamically converts them to `age__gt` or `age__lt` database queries.
- **Custom Mapping:** Hardcodes the project-specific definition of "young" to dynamically apply an `age__gte=16` and `age__lte=24` filter.

**3. Edge Case Handling**
- **Contradictory Logic:** If the parser detects *both* "male" and "female" in the same query (e.g., "male and female teenagers"), it deliberately sets `matched = True` but ignores applying any gender filter, allowing the database to accurately return both.
- **Case-Insensitive Geography:** Regex extractions for countries (e.g., extracting "nigeria" from "from nigeria") are passed to a Django `__iexact` lookup to safely cross-reference capitalized database entries.
