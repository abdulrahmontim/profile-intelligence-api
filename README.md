# Profile Intelligence API

A RESTful API for retrieving and analyzing user profile intelligence data.

## 🚀 Live API

**Deployed:** https://profile-intelligence-api.up.railway.app

## Features

- **Profile Intelligence Analysis**: Automatically analyze names to predict gender, age, and nationality
- **Gender Prediction**: Determine gender with confidence scores and sample size data
- **Age Estimation**: Estimate age ranges and categorize into demographic groups (child, teenager, adult, senior)
- **Nationality Detection**: Identify likely countries of origin with probability scores
- **Idempotent Operations**: Prevent duplicate profiles - same name returns existing data
- **Advanced Filtering**: Filter profiles by gender, country, and age group with case-insensitive search
- **RESTful API**: Clean, standardized API endpoints following REST principles
- **Real-time Data**: Fetch live intelligence data from external APIs (Genderize, Agify, Nationalize)
- **UUID7 Primary Keys**: Time-ordered unique identifiers for better database performance
- **Comprehensive Error Handling**: Detailed error responses for API failures and invalid requests

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/abdulrahmontim/profile-intelligence-api.git
    cd profile-intelligence-api
    ```

2. Create and activate virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4. Run migrations:
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

5. Start the development server:
    ```bash
    python manage.py runserver
    ```

## Usage

**Local Development:** http://localhost:8000

## API Endpoints

### 1. Create Profile
**POST** `/api/profiles`

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
    "country_id": "DRC",
    "country_probability": 0.85,
    "created_at": "2026-04-01T12:00:00Z"
  }
}
```

**Idempotency:** If the same name is submitted again, returns existing profile:
```json
{
  "status": "success",
  "message": "Profile already exists",
  "data": { "...existing profile..." }
}
```

### 2. Get Profile by ID
**GET** `/api/profiles/{id}`

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
**GET** `/api/profiles`

**Optional Query Parameters** (case-insensitive):
- `gender` - Filter by gender (male/female)
- `country_id` - Filter by country code (e.g., NG, US)
- `age_group` - Filter by age group (child/teenager/adult/senior)

**Example:** `/api/profiles?gender=male&country_id=NG`

**Success Response (200):**
```json
{
  "status": "success",
  "count": 2,
  "data": [
    {
      "id": "id-1",
      "name": "emmanuel",
      "gender": "male",
      "age": 25,
      "age_group": "adult",
      "country_id": "NG"
    },
    {
      "id": "id-2",
      "name": "sarah",
      "gender": "female",
      "age": 28,
      "age_group": "adult",
      "country_id": "US"
    }
  ]
}
```

### 4. Delete Profile
**DELETE** `/api/profiles/{id}`

**Success Response:** `204 No Content`
