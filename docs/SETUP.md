# 🛠️ Development Setup Guide

Complete guide to get the NU Launch Labs backend running on your machine.

---

## Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.12+ | https://python.org/downloads/ |
| Docker Desktop | Latest | https://docker.com/products/docker-desktop/ |
| Git | Latest | https://git-scm.com/downloads |

Verify Python:
```bash
python --version
# Should show Python 3.12.x

# If you have multiple versions on Windows:
py -3.12 --version
```

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/nu-launchlabs/null-db-backend.git
cd null-db-backend
```

---

## Step 2: Create Virtual Environment

```bash
python -m venv venv

# Windows PowerShell:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate
```

You should see `(venv)` at the start of your prompt. **Always activate before running any commands.**

If you have multiple Python versions on Windows:
```powershell
py -3.12 -m venv venv
venv\Scripts\activate
```

---

## Step 3: Install Dependencies

```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Install all dev dependencies
pip install -r requirements/dev.txt
```

This installs:
- Django 5.1.4 — web framework
- djangorestframework 3.15.2 — REST API layer
- djangorestframework-simplejwt 5.4.0 — JWT authentication
- psycopg2-binary 2.9.10 — PostgreSQL adapter
- django-cors-headers 4.6.0 — CORS for frontend
- django-filter 24.3 — queryset filtering
- drf-spectacular 0.28.0 — Swagger/OpenAPI docs
- python-decouple 3.8 — environment variables
- pytest 8.3.4 — test framework
- pytest-django 4.9.0 — Django test integration
- pytest-cov 6.0.0 — test coverage
- factory-boy 3.3.1 — test data factories
- ruff 0.8.4 — linter
- black 24.10.0 — code formatter
- django-debug-toolbar 4.4.6 — debug tools

Verify Django installed:
```bash
python -c "import django; print(django.get_version())"
# Should print: 5.1.4
```

---

## Step 4: Environment Variables

```bash
# Copy the example file
# Windows PowerShell:
Copy-Item .env.example .env

# Mac/Linux:
cp .env.example .env
```

Generate a SECRET_KEY:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Open `.env` in your editor and paste the generated key as the `SECRET_KEY` value. Leave all other values as defaults for local development.

**.env file contents:**
```
SECRET_KEY=your-generated-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=nulaunchlabs
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

ACCESS_TOKEN_LIFETIME_MINUTES=30
REFRESH_TOKEN_LIFETIME_DAYS=7

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

⚠️ **NEVER commit `.env` to git.** It's already in `.gitignore`.

---

## Step 5: Start PostgreSQL via Docker

Make sure Docker Desktop is running (check the system tray icon).

```bash
docker compose up db -d
```

Verify it's running:
```bash
docker compose ps
```

Expected output:
```
NAME            IMAGE                  STATUS          PORTS
nll_postgres    postgres:16-alpine     Up (healthy)    0.0.0.0:5432->5432/tcp
```

Wait until it says "healthy" before continuing.

---

## Step 6: Run Database Migrations

```bash
# Generate migration files (first time only)
python manage.py makemigrations accounts

# Apply all migrations
python manage.py migrate
```

Expected output:
```
   Migrations for 'accounts':
     apps/accounts/migrations/0001_initial.py
     apps/accounts/migrations/0002_generalinterest.py
   Migrations for 'cycles':
     apps/cycles/migrations/0001_initial.py
   Migrations for 'audit':
     apps/audit/migrations/0001_initial.py

Operations to perform:
  Apply all migrations: accounts, admin, auth, contenttypes, sessions
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying accounts.0001_initial... OK
  Applying admin.0001_initial... OK
  ...
```

---

## Step 7: Create Admin (Superuser) Account

```bash
python manage.py createsuperuser
```

Enter when prompted:
```
Email: admin@northeastern.edu
First name: Admin
Last name: User
Password: AdminPass123!
Password (again): AdminPass123!
```

Use a `@northeastern.edu` email. Remember the password.

---

## Step 8: Start the Dev Server

```bash
python manage.py runserver
```

Expected output:
```
Starting development server at http://127.0.0.1:8000/
```

---

## Step 9: Verify Everything Works

| What to Check | URL | Expected |
|--------------|-----|----------|
| Swagger UI | http://127.0.0.1:8000/api/v1/docs/ | Interactive API docs with all endpoints |
| ReDoc | http://127.0.0.1:8000/api/v1/redoc/ | Alternative API docs |
| Django Admin | http://127.0.0.1:8000/admin/ | Login with superuser credentials |

---

## Step 10: Run Tests

Open a new terminal (keep server running or stop it):

```bash
# Make sure venv is activated
venv\Scripts\activate   # Windows
source venv/bin/activate # Mac/Linux

# Run all tests
pytest -v

# Run with coverage report
pytest --cov=apps --cov-report=term-missing -v

# Run specific test class
pytest apps/accounts/tests/test_auth.py::TestRegistration -v
```

Expected: **90+ passed, 0 failed**

---

## Common Commands

| Command | Description |
|---------|-------------|
| `python manage.py runserver` | Start dev server |
| `python manage.py makemigrations` | Generate migration files after model changes |
| `python manage.py migrate` | Apply migrations to database |
| `python manage.py createsuperuser` | Create admin user |
| `python manage.py shell` | Open Python shell with Django loaded |
| `docker compose up db -d` | Start PostgreSQL container |
| `docker compose down` | Stop all containers |
| `docker compose ps` | Check container status |
| `pytest -v` | Run all tests |
| `pytest --cov=apps -v` | Run tests with coverage |
| `ruff check .` | Run linter |
| `black .` | Format code |

---

## Troubleshooting

### "Could not connect to server" on migrate
PostgreSQL isn't running.
```bash
docker compose up db -d
docker compose ps  # wait for "healthy"
```

### "ModuleNotFoundError: No module named 'apps'"
Missing `__init__.py` file.
```powershell
# Windows:
New-Item -ItemType File -Force -Path apps\__init__.py
```

### "SECRET_KEY not found" or "ImproperlyConfigured"
`.env` file is missing or not in the project root (same folder as `manage.py`).

### "relation 'users' does not exist"
Migrations haven't been applied.
```bash
python manage.py migrate
```

### pip can't find Django 5.1.4
You're using an old Python version. Check with `python --version`. Need 3.10+ for Django 5.x.

### Tests fail with database errors
Make sure PostgreSQL is running. Tests create their own temporary database automatically.

### "touch is not recognized" (Windows)
Use PowerShell's `New-Item` instead:
```powershell
New-Item -ItemType File -Force -Path filename.py
```

---

## Notes for Windows Users

- Use **PowerShell**, not Command Prompt
- Use `venv\Scripts\activate` (backslashes)
- `touch` doesn't exist — use `New-Item -ItemType File -Path filename`
- `cp` doesn't exist — use `Copy-Item source dest`
- `make` commands from Makefile might not work — run the Python commands directly