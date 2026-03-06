# 🚀 NU Launch Labs — Backend

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org/)
[![Django](https://img.shields.io/badge/Django-5.1-green.svg)](https://djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15-red.svg)](https://django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://postgresql.org/)
[![JWT](https://img.shields.io/badge/Auth-JWT-orange.svg)](https://jwt.io/)

Backend API for the NU Launch Labs application cycle management platform. Manages semester-long application cycles where Northeastern students apply to startup projects (Launch Track) or propose their own (Innovation Track).

## 📋 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Architecture](#-architecture)
- [Getting Started](#-getting-started)
- [API Documentation](#-api-documentation)
- [Project Structure](#-project-structure)
- [Development Progress](#-development-progress)

## ✨ Features

### Phase 1: Foundation ✅

#### Authentication & Authorization
- [x] User registration with NEU email validation (@northeastern.edu, @husky.neu.edu)
- [x] JWT-based authentication (access + refresh tokens)
- [x] Token refresh with rotation and blacklisting
- [x] Password change with current password verification
- [x] Role-based access control (ADMIN, OPS_CHAIR, USER, LAUNCH_TEAM)
- [x] Custom permission classes (composable, stackable)

#### User Management
- [x] Self-registration for NEU students (auto-assigns USER role)
- [x] Admin creates Launch Team accounts (any email domain allowed)
- [x] Admin role management with email-role compatibility checks
- [x] User listing with role filtering and name/email search
- [x] Profile viewing and editing (own profile only)

### Phase 2: Cycle Management + General Interest + Audit ✅

#### Application Cycles
- [x] Semester-level cycle container (e.g. "Fall 2026")
- [x] Two independent track toggles: `launch_open` and `innovation_open`
- [x] Admin can open/close each track independently at any time
- [x] Both tracks can run simultaneously
- [x] Cycle close operation (one-way, deactivates cycle)
- [x] Cycle statistics dashboard

#### General Interest Form
- [x] Students submit GI form anytime during active cycle (not phase-gated)
- [x] Upsert pattern: resubmitting updates existing form (always editable)
- [x] Completing GI sets `is_gi_complete` flag for downstream permissions
- [x] One GI per user per cycle (DB constraint)

#### Audit Logging
- [x] Immutable, append-only audit trail
- [x] Every service method logs to AuditService
- [x] Tracks actor, action, target, metadata, and IP address
- [x] Filterable audit log viewer (Admin/Ops Chair)
- [x] Retroactively wired into all Phase 1 endpoints

#### Infrastructure
- [x] PostgreSQL 16 via Docker
- [x] Swagger UI + ReDoc API documentation
- [x] Custom exception handler (consistent error format)
- [x] CORS configured for Next.js frontend
- [x] 90+ automated tests with pytest


## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Framework** | Django 5.1 |
| **API Layer** | Django REST Framework 3.15 |
| **Database** | PostgreSQL 16 |
| **Auth** | SimpleJWT |
| **API Docs** | drf-spectacular |
| **Testing** | pytest + factory-boy |
| **Container** | Docker + docker-compose |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Client Layer                          │
│                  (Next.js Frontend / Swagger)               │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP/HTTPS + JWT
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   Django + DRF Application                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   accounts  │  cycles  │  launch  │  innovation  │  audit   │
│             │          │          │              │          │
│             │          │          │              │          │
├─────────────────────────────────────────────────────────────┤
│                    Service Layer                            │
│         (All business logic, validation, rules)             │
├─────────────────────────────────────────────────────────────┤
│                    Django ORM                               │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │ PostgreSQL  │
                   │    16       │
                   └─────────────┘
```

### Service Layer Pattern

```
Request → View (thin controller) → Service (business logic) → Model (ORM) → DB
            │                         │
            ├── Serializer            ├── Audit logging
            │   (validates input)     ├── Email notifications
            │                         └── Constraint checks
            └── Permission classes
                (role-based access)
```

No business logic in views. No database queries in views. Views only validate input, call service, return response.

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- Docker Desktop
- Git

### 1. Clone Repository

```bash
git clone https://github.com/nu-launchlabs/null-db-backend.git
cd null-db-backend
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows PowerShell:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements/dev.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Generate a SECRET_KEY and paste it into `.env`:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. Start PostgreSQL

```bash
docker compose up db -d

# Verify
docker compose ps
# Should show nll_postgres as "Up (healthy)"
```

### 6. Run Migrations

```bash
python manage.py migrate
```

### 7. Create Admin Account

```bash
python manage.py createsuperuser
# Use an @northeastern.edu email
```

### 8. Start Server

```bash
python manage.py runserver
```

### 9. Access the Application

| URL | Description |
|-----|-------------|
| http://127.0.0.1:8000/api/v1/docs/ | Swagger UI — test all endpoints |
| http://127.0.0.1:8000/api/v1/redoc/ | ReDoc — alternative API docs |
| http://127.0.0.1:8000/admin/ | Django Admin panel |

## 📚 API Documentation

### Authentication (Phase 1)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/register/` | None | Register NEU student |
| POST | `/api/v1/auth/login/` | None | Login, get JWT tokens |
| POST | `/api/v1/auth/token/refresh/` | None | Refresh access token |
| GET | `/api/v1/auth/me/` | Any | Get own profile |
| PATCH | `/api/v1/auth/me/` | Any | Update own profile |
| POST | `/api/v1/auth/change-password/` | Any | Change own password |
| POST | `/api/v1/auth/launch-team/` | Admin | Create Launch Team account |
| GET | `/api/v1/auth/users/` | Admin, Ops | List all users |
| PATCH | `/api/v1/auth/users/{id}/role/` | Admin | Change user role |

### Application Cycles (Phase 2)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/cycles/` | Admin | Create new cycle |
| GET | `/api/v1/cycles/list/` | Admin, Ops | List all cycles |
| GET | `/api/v1/cycles/current/` | Any | Get active cycle |
| PATCH | `/api/v1/cycles/{id}/toggles/` | Admin | Update track toggles |
| POST | `/api/v1/cycles/{id}/close/` | Admin | Close cycle (permanent) |
| GET | `/api/v1/cycles/{id}/stats/` | Admin, Ops | Cycle statistics |

### General Interest (Phase 2)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/general-interest/` | Student | Submit or update GI form |
| GET | `/api/v1/auth/general-interest/me/` | Any | View own GI submission |

### Audit (Phase 2)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/audit/logs/` | Admin, Ops | View audit trail |

### Error Response Format

All errors return a consistent structure:

```json
{
  "error": {
    "code": "business_logic_error",
    "message": "Human readable message",
    "details": null
  }
}
```

## 📁 Project Structure

```
nu-launch-labs/
├── config/                    # Django settings, root URLs, wsgi/asgi
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── accounts/              # Users, auth, registration, roles, GI
│   │   ├── models.py          # User model + GeneralInterest model
│   │   ├── managers.py        # Custom UserManager (email-based)
│   │   ├── serializers.py     # DTOs (register, login, profile, GI, etc.)
│   │   ├── services.py        # Business logic (register, GI upsert, etc.)
│   │   ├── views.py           # Thin controllers
│   │   ├── urls.py            # Route mapping
│   │   ├── permissions.py     # IsAdmin, IsOpsChair, IsGIComplete, etc.
│   │   ├── validators.py      # NEU email domain validation
│   │   ├── admin.py           # Django Admin configuration
│   │   └── tests/
│   │       ├── test_auth.py   # Auth tests (31)
│   │       └── test_gi.py     # GI tests (20+)
│   ├── cycles/                # Application cycle management
│   │   ├── models.py          # ApplicationCycle with independent toggles
│   │   ├── serializers.py     # Cycle DTOs
│   │   ├── services.py        # Cycle lifecycle, toggle management
│   │   ├── views.py           # Cycle endpoints
│   │   ├── urls.py            # Route mapping
│   │   ├── admin.py           # Django Admin configuration
│   │   └── tests/
│   │       └── test_cycles.py # Cycle tests (30+)
│   ├── launch/                # Launch track (Phase 3)
│   ├── innovation/            # Innovation track (Phase 4)
│   ├── audit/                 # Audit logging
│   │   ├── models.py          # AuditLog model (immutable)
│   │   ├── serializers.py     # Audit DTOs
│   │   ├── services.py        # AuditService.log()
│   │   ├── views.py           # Audit log viewer
│   │   ├── urls.py            # Route mapping
│   │   ├── admin.py           # Django Admin (read-only)
│   │   └── tests/
│   │       └── test_audit.py  # Audit tests (15+)
│   └── notifications/         # Email system (Phase 5)
├── utils/
│   ├── exceptions.py          # Custom exceptions + error handler
│   ├── pagination.py          # Standard pagination config
│   ├── mixins.py              # TimestampMixin (created_at, updated_at)
│   └── constants.py           # NEU_EMAIL_DOMAINS, etc.
├── docs/
│   ├── API.md                 # Detailed API documentation
│   ├── DATABASE_SCHEMA.md     # Full database schema
│   └── SETUP.md               # Development setup guide
├── requirements/
│   ├── base.txt               # Production dependencies
│   ├── dev.txt                # Dev tools (pytest, ruff, etc.)
│   └── prod.txt               # Gunicorn, etc.
├── docker-compose.yml
├── Dockerfile
├── manage.py
└── pytest.ini
```

## 🔐 Roles & Permissions

| Role | Who | Email Requirement | How They're Created |
|------|-----|-------------------|-------------------|
| **ADMIN** | Club leadership | NEU email required | Promoted by superuser/admin |
| **OPS_CHAIR** | Operations team | NEU email required | Promoted by admin |
| **USER** | NEU students | NEU email required | Self-registration |
| **LAUNCH_TEAM** | External startups | Any email allowed | Admin creates account |

## 🧪 Running Tests

```bash
# All tests
pytest -v

# With coverage
pytest --cov=apps --cov-report=term-missing -v

# Specific test class
pytest apps/accounts/tests/test_auth.py::TestRegistration -v

# Phase 2 tests only
pytest apps/cycles/tests/ apps/audit/tests/ apps/accounts/tests/test_gi.py -v
```

## 🔧 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | (generate one) |
| `DEBUG` | Enable debug mode | `True` |
| `DB_NAME` | PostgreSQL database | `nulaunchlabs` |
| `DB_USER` | PostgreSQL user | `postgres` |
| `DB_PASSWORD` | PostgreSQL password | `postgres` |
| `DB_HOST` | Database host | `localhost` |
| `DB_PORT` | Database port | `5432` |
| `CORS_ALLOWED_ORIGINS` | Frontend URLs | `http://localhost:3000` |
| `ACCESS_TOKEN_LIFETIME_MINUTES` | JWT access token TTL | `30` |
| `REFRESH_TOKEN_LIFETIME_DAYS` | JWT refresh token TTL | `7` |

## 👥 Team

| Member | Owns | Focus Area |
|--------|------|------------|
| **Thejesh** | accounts, cycles, innovation, audit, utils | Auth, cycle management, Innovation workflow |