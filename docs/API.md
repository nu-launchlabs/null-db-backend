# 📚 API Documentation

Base URL: `http://127.0.0.1:8000/api/v1/`

Interactive Docs: [Swagger UI](http://127.0.0.1:8000/api/v1/docs/) | [ReDoc](http://127.0.0.1:8000/api/v1/redoc/)

---

## 🔐 Authentication

All endpoints except Register, Login, and Token Refresh require a JWT token in the header:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

- Access tokens expire after **30 minutes**
- Refresh tokens expire after **7 days**
- Refresh tokens rotate on use (old one is blacklisted)

---

## Phase 1 Endpoints (9 total)

### POST `/auth/register/`

Register a new student account. Only Northeastern emails accepted.

**Auth Required:** No

**Request Body:**
```json
{
  "email": "john.doe@northeastern.edu",
  "password": "SecurePass123!",
  "confirm_password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Success Response (201 Created):**
```json
{
  "message": "Registration successful.",
  "user": {
    "id": 2,
    "email": "john.doe@northeastern.edu",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "role": "USER",
    "is_gi_complete": false,
    "is_neu_email": true,
    "created_at": "2026-02-21T20:30:00Z",
    "updated_at": "2026-02-21T20:30:00Z"
  }
}
```

**Error Responses:**
| Status | Reason |
|--------|--------|
| 400 | Non-NEU email, weak password, passwords don't match, missing fields |
| 409 | Email already exists |

---

### POST `/auth/login/`

Login and receive JWT tokens + user profile.

**Auth Required:** No

**Request Body:**
```json
{
  "email": "john.doe@northeastern.edu",
  "password": "SecurePass123!"
}
```

**Success Response (200 OK):**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIs...",
  "refresh": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": 2,
    "email": "john.doe@northeastern.edu",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "role": "USER",
    "is_gi_complete": false,
    "is_neu_email": true,
    "created_at": "2026-02-21T20:30:00Z",
    "updated_at": "2026-02-21T20:30:00Z"
  }
}
```

**Error Responses:**
| Status | Reason |
|--------|--------|
| 401 | Invalid email or password |

**JWT Token Claims:**
The access token contains these custom claims:
- `role` — user's role (ADMIN, OPS_CHAIR, USER, LAUNCH_TEAM)
- `email` — user's email
- `full_name` — user's full name

---

### POST `/auth/token/refresh/`

Get a new access token using a valid refresh token.

**Auth Required:** No (but needs valid refresh token)

**Request Body:**
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Success Response (200 OK):**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIs...",
  "refresh": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Notes:**
- Old refresh token is blacklisted after use (can't reuse)
- New refresh token is issued (rotation)

---

### GET `/auth/me/`

Get the currently authenticated user's profile.

**Auth Required:** Any authenticated user

**Success Response (200 OK):**
```json
{
  "id": 2,
  "email": "john.doe@northeastern.edu",
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe",
  "role": "USER",
  "is_gi_complete": false,
  "is_neu_email": true,
  "created_at": "2026-02-21T20:30:00Z",
  "updated_at": "2026-02-21T20:30:00Z"
}
```

---

### PATCH `/auth/me/`

Update the currently authenticated user's profile. Only name fields can be changed.

**Auth Required:** Any authenticated user

**Request Body (partial update):**
```json
{
  "first_name": "Jonathan"
}
```

**Success Response (200 OK):** Updated user profile (same shape as GET /auth/me/)

---

### POST `/auth/change-password/`

Change the currently authenticated user's password.

**Auth Required:** Any authenticated user

**Request Body:**
```json
{
  "current_password": "SecurePass123!",
  "new_password": "NewSecurePass456!",
  "confirm_new_password": "NewSecurePass456!"
}
```

**Success Response (200 OK):**
```json
{
  "message": "Password changed successfully."
}
```

**Error Responses:**
| Status | Reason |
|--------|--------|
| 400 | Wrong current password, weak new password, passwords don't match |

---

### POST `/auth/launch-team/`

Admin creates a Launch Team account. Any email domain is allowed.

**Auth Required:** ADMIN only

**Request Body:**
```json
{
  "email": "founder@techstartup.com",
  "password": "TempPass123!",
  "first_name": "Jane",
  "last_name": "Founder"
}
```

**Success Response (201 Created):**
```json
{
  "message": "Launch Team account created.",
  "user": {
    "id": 3,
    "email": "founder@techstartup.com",
    "first_name": "Jane",
    "last_name": "Founder",
    "full_name": "Jane Founder",
    "role": "LAUNCH_TEAM",
    "is_gi_complete": false,
    "is_neu_email": false,
    "created_at": "2026-02-21T21:00:00Z",
    "updated_at": "2026-02-21T21:00:00Z"
  }
}
```

**Error Responses:**
| Status | Reason |
|--------|--------|
| 400 | Validation error |
| 403 | Not an admin |
| 409 | Email already exists |

---

### GET `/auth/users/`

List all users. Supports filtering and search.

**Auth Required:** ADMIN or OPS_CHAIR

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `role` | string | Filter by role: ADMIN, OPS_CHAIR, USER, LAUNCH_TEAM |
| `is_gi_complete` | boolean | Filter by GI completion status |
| `search` | string | Search by name or email |

**Example:** `GET /auth/users/?role=USER&search=john`

**Success Response (200 OK):**
```json
[
  {
    "id": 2,
    "email": "john.doe@northeastern.edu",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "role": "USER",
    "is_gi_complete": false,
    "is_neu_email": true,
    "is_active": true,
    "created_at": "2026-02-21T20:30:00Z"
  }
]
```

---

### PATCH `/auth/users/{user_id}/role/`

Admin changes a user's role.

**Auth Required:** ADMIN only

**URL Params:** `user_id` — integer ID of the user

**Request Body:**
```json
{
  "role": "OPS_CHAIR"
}
```

**Success Response (200 OK):** Updated user profile

**Business Rules:**
- Cannot change your own role
- Non-NEU email users can only have LAUNCH_TEAM role
- ADMIN, OPS_CHAIR, USER roles require a Northeastern email

**Error Responses:**
| Status | Reason |
|--------|--------|
| 400 | Can't change own role, email-role incompatibility |
| 403 | Not an admin |
| 404 | User not found |

---

## 🚨 Error Response Format

Every error returns this consistent structure:

```json
{
  "error": {
    "code": "business_logic_error",
    "message": "Human readable description of what went wrong",
    "details": null
  }
}
```

For validation errors, `details` has field-level info:

```json
{
  "error": {
    "code": "invalid",
    "message": "Validation error",
    "details": {
      "email": ["A Northeastern email is required (@northeastern.edu or @husky.neu.edu)."],
      "password": ["This password is too common."]
    }
  }
}
```

## 📊 Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created successfully |
| 400 | Bad request / validation error / business rule violated |
| 401 | Not authenticated (missing or invalid token) |
| 403 | Forbidden (authenticated but wrong role) |
| 404 | Resource not found |
| 409 | Conflict (duplicate data) |
| 429 | Rate limited (too many requests) |
| 500 | Internal server error |

## 🔒 Permission Matrix

| Endpoint | ADMIN | OPS_CHAIR | USER | LAUNCH_TEAM | Anonymous |
|----------|-------|-----------|------|-------------|-----------|
| POST /auth/register/ | — | — | — | — | ✅ |
| POST /auth/login/ | ✅ | ✅ | ✅ | ✅ | ✅ |
| POST /auth/token/refresh/ | ✅ | ✅ | ✅ | ✅ | ✅ |
| GET /auth/me/ | ✅ | ✅ | ✅ | ✅ | ❌ 401 |
| PATCH /auth/me/ | ✅ | ✅ | ✅ | ✅ | ❌ 401 |
| POST /auth/change-password/ | ✅ | ✅ | ✅ | ✅ | ❌ 401 |
| POST /auth/launch-team/ | ✅ | ❌ 403 | ❌ 403 | ❌ 403 | ❌ 401 |
| GET /auth/users/ | ✅ | ✅ | ❌ 403 | ❌ 403 | ❌ 401 |
| PATCH /auth/users/{id}/role/ | ✅ | ❌ 403 | ❌ 403 | ❌ 403 | ❌ 401 |