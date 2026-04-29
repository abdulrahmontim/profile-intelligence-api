# Insighta Labs+ — Profile Intelligence API

A secure, multi-interface platform for querying and managing profile intelligence data.
Built for analysts, engineers, and internal stakeholders across CLI and web interfaces.

---

## System Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    CLI Tool      │     │   Web Portal     │     │   REST Client   │
│  (insighta-cli) │     │ (insighta-web)   │     │ (Postman/curl)  │
└────────┬─────────┘     └────────┬─────────┘     └────────┬────────┘
         │                        │                         │
         └────────────────────────┼─────────────────────────┘
                                  │
                       ┌──────────▼──────────┐
                       │   Django Backend     │
                       │   REST API           │
                       │   (Railway)          │
                       └──────────┬──────────┘
                                  │
               ┌──────────────────┼──────────────────┐
               │                  │                  │
      ┌────────▼────────┐  ┌──────▼──────┐  ┌───────▼────────┐
      │   PostgreSQL     │  │   GitHub    │  │  External APIs  │
      │   (Railway)      │  │   OAuth     │  │  genderize.io  │
      └──────────────────┘  └─────────────┘  │  agify.io      │
                                              │  nationalize.io│
                                              └────────────────┘
```

### Repositories
| Repo | Description |
|------|-------------|
| `profile-intelligence-api` | Django REST API backend |
| `profile-intelligence-cli` | Command line tool |
| `profile-intelligence-web` | Web portal |

All three interfaces share the same backend. Data is consistent across all of them.

---

## Authentication Flow

### Web Flow (Browser)
```
Browser                     Backend                    GitHub
   |                           |                          |
   |-- GET /auth/github ------->|                          |
   |                           |-- generate verifier      |
   |                           |-- generate challenge     |
   |                           |-- generate state         |
   |                           |-- store in session       |
   |<-- redirect to GitHub ----|                          |
   |                                                      |
   |-- authorize on GitHub ----------------------------- >|
   |<-- redirect to /auth/github/callback?code=&state= --|
   |                           |                          |
   |-- GET /callback --------> |                          |
   |                           |-- validate state         |
   |                           |-- exchange code+verifier |
   |                           |-- fetch github user      |
   |                           |-- create/update user     |
   |                           |-- issue token pair       |
   |<-- access + refresh token-|                          |
```

### CLI Flow
```
Terminal              Local Server (port 9876)        Backend
   |                          |                          |
   |-- insighta login ------> |                          |
   |-- generate PKCE locally  |                          |
   |-- open browser           |                          |
   |                          |<-- GitHub callback ------|
   |                          |-- capture code+state     |
   |<-- code received --------|                          |
   |-- POST code+verifier ---------------------------->  |
   |<-- access + refresh token -----------------------   |
   |-- save to ~/.insighta/credentials.json              |
   |-- "Logged in as @username"                          |
```

### Token Lifecycle
| Token | Expiry | Storage |
|-------|--------|---------|
| Access token | 3 minutes | CLI: credentials.json / Web: HttpOnly cookie |
| Refresh token | 5 minutes | DB (invalidated on use) |

- Each refresh issues a **new pair** and immediately invalidates the old one
- Logout invalidates the refresh token server-side
- Expired access token → auto-refresh attempted → re-login if refresh also expired

---

## User Roles

| Role | Permissions |
|------|-------------|
| `admin` | Create profiles, delete profiles, read, search, export |
| `analyst` | Read, search, export only |

Default role on first login: `analyst`

To promote a user to admin:
```bash
python manage.py shell
```
```python
from users.models import User
user = User.objects.get(username="github_username")
user.role = "admin"
user.save()
```

---

## API Endpoints

### Auth Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auth/github` | Redirect to GitHub OAuth |
| GET | `/auth/github/callback` | Handle OAuth callback, issue tokens |
| POST | `/auth/refresh` | Rotate refresh token, issue new pair |
| POST | `/auth/logout` | Invalidate refresh token server-side |

#### POST /auth/refresh
```json
// Request
{ "refresh_token": "string" }

// Response
{
  "status": "success",
  "access_token": "string",
  "refresh_token": "string"
}
```

#### POST /auth/logout
```json
// Request
{ "refresh_token": "string" }

// Response
{ "status": "success", "message": "Logged out" }
```

---

### Profile Endpoints
All profile endpoints require:
- `Authorization: Bearer <access_token>` header
- `X-API-Version: 1` header

Requests missing `X-API-Version` return:
```json
{ "status": "error", "message": "API version header required" }
```
Status: `400 Bad Request`

| Method | Endpoint | Role Required |
|--------|----------|--------------|
| GET | `/api/profiles` | analyst, admin |
| POST | `/api/profiles` | admin |
| GET | `/api/profiles/<id>` | analyst, admin |
| DELETE | `/api/profiles/<id>` | admin |
| GET | `/api/profiles/search?q=` | analyst, admin |
| GET | `/api/profiles/export?format=csv` | analyst, admin |

#### GET /api/profiles — Paginated Response
```json
{
  "status": "success",
  "page": 1,
  "limit": 10,
  "total": 2026,
  "total_pages": 203,
  "links": {
    "self": "/api/profiles?page=1&limit=10",
    "next": "/api/profiles?page=2&limit=10",
    "prev": null
  },
  "data": [ ... ]
}
```

Supports filters: `?gender=male&country=NG&age_group=adult&min_age=20&max_age=40`
Supports sorting: `?sort_by=age&order=desc`

#### POST /api/profiles
```json
// Request
{ "name": "Harriet Tubman" }

// Response
{
  "status": "success",
  "data": {
    "id": "uuid",
    "name": "harriet tubman",
    "gender": "female",
    "gender_probability": 0.97,
    "age": 28,
    "age_group": "adult",
    "country_id": "US",
    "country_name": "United States",
    "country_probability": 0.89,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

#### GET /api/profiles/export?format=csv
Returns a CSV file download.
- Content-Type: `text/csv`
- Columns: `id, name, gender, gender_probability, age, age_group, country_id, country_name, country_probability, created_at`
- Supports same filters as GET /api/profiles

---

## Role Enforcement Logic

Enforced via two layers that work together:

**Layer 1 — `JWTAuthMiddleware`** runs on every request:
- Reads `Authorization: Bearer <token>` header
- Decodes JWT, fetches user from DB
- Attaches user to `request.auth_user`
- Sets `request.auth_user = None` on any failure

**Layer 2 — RBAC decorators** on each view:
```python
@method_decorator(require_analyst_or_admin, name="get")   # read
@method_decorator(require_admin, name="post")              # write
class ProfileListCreateView(APIView):
    ...
```

Available decorators:
- `require_auth` — any authenticated user
- `require_role("admin", "analyst")` — specific roles
- `require_admin` — admin only (alias)
- `require_analyst_or_admin` — both roles (alias)

Response codes:
- `401` — no token or invalid token
- `403` — authenticated but wrong role or inactive account

---

## Natural Language Search

Endpoint: `GET /api/profiles/search?q=young males from nigeria`

Queries are parsed into structured DB filters using keyword matching:

| Query Keywords | Maps To |
|----------------|---------|
| young, adult | `age_group=adult` |
| child, teenager, senior | `age_group=<value>` |
| male, males, man, men | `gender=male` |
| female, females, woman, women | `gender=female` |
| from nigeria, nigerian | `country_id=NG` |
| from usa, american | `country_id=US` |

Example:
```
"young females from the US" → { gender: female, age_group: adult, country_id: US }
```

---

## CLI Usage

### Installation
```bash
git clone https://github.com/abdulrahmontim/profile-intelligence-cli
cd profile-intelligence-cli
pip install -e .
```

After installation, `insighta` works from any directory.

### Auth Commands
```bash
insighta login       # opens GitHub OAuth in browser
insighta logout      # invalidates tokens
insighta whoami      # shows current user
```

### Profile Commands
```bash
# List profiles
insighta profiles list
insighta profiles list --gender male
insighta profiles list --country NG --age-group adult
insighta profiles list --min-age 25 --max-age 40
insighta profiles list --sort-by age --order desc
insighta profiles list --page 2 --limit 20

# Get single profile
insighta profiles get <id>

# Search
insighta profiles search "young males from nigeria"

# Create (admin only)
insighta profiles create --name "Harriet Tubman"

# Export
insighta profiles export --format csv
insighta profiles export --format csv --gender male --country NG
```

### Token Handling
- Tokens stored at `~/.insighta/credentials.json`
- Every request sends `Authorization: Bearer <access_token>`
- On `401` response → auto-refresh attempted using refresh token
- If refresh fails → user prompted to run `insighta login` again

---

## Local Setup

### Requirements
- Python 3.12+
- PostgreSQL (or SQLite for local dev)

### Steps
```bash
git clone https://github.com/abdulrahmontim/profile-intelligence-api
cd profile-intelligence-api

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

python manage.py migrate
python manage.py seed_profiles
python manage.py runserver
```

### Environment Variables
Create a `.env` file in the project root:
```bash
SECRET_KEY=your-django-secret-key
DEBUG=True
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
GITHUB_REDIRECT_URI=http://127.0.0.1:8000/auth/github/callback
JWT_SECRET=your-jwt-secret
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=localhost,127.0.0.1
```

---

## Deployment

- Backend hosted on **Railway**
- PostgreSQL database hosted on **Railway**
- Auto-deploys on push to `main`

### Railway Commands
**Pre-deploy:**
```
python manage.py migrate && python manage.py seed_profiles
```

**Start:**
```
gunicorn profile_intelligence.wsgi:application --bind 0.0.0.0:$PORT
```

---

## Rate Limiting

| Scope | Limit |
|-------|-------|
| `/auth/*` endpoints | 10 requests / minute |
| `/api/*` endpoints | 60 requests / minute per user |

Returns `429 Too Many Requests` when exceeded.

---

## CI/CD

GitHub Actions runs on every PR to `main`:
- Linting with `flake8`
- Django migrations check
- Test suite

See `.github/workflows/ci.yml` for full configuration.

---

## Error Response Format

All errors follow this structure:
```json
{
  "status": "error",
  "message": "Human readable message"
}
```

---

## Live URLs

- **Backend API:** https://profile-intelligence-api-production.up.railway.app
- **Web Portal:** https://profile-intelligence-web.up.railway.app