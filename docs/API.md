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

## Phase 2 Endpoints (9 total)

### POST `/cycles/`

Create a new application cycle. Only one active cycle can exist at a time.

**Auth Required:** ADMIN only

**Request Body:**
```json
{
  "name": "Fall 2026",
  "description": "Fall semester application cycle"
}
```

**Success Response (201 Created):**
```json
{
  "message": "Application cycle created.",
  "cycle": {
    "id": 1,
    "name": "Fall 2026",
    "is_active": true,
    "launch_open": false,
    "innovation_open": false,
    "description": "Fall semester application cycle",
    "created_at": "2026-03-05T10:00:00Z",
    "updated_at": "2026-03-05T10:00:00Z"
  }
}
```

New cycles start with both toggles OFF. Admin decides when to open each track.

**Error Responses:**
| Status | Reason |
|--------|--------|
| 400 | Validation error, duplicate name |
| 403 | Not an admin |
| 409 | An active cycle already exists |

---

### GET `/cycles/list/`

List all cycles (active and closed).

**Auth Required:** ADMIN or OPS_CHAIR

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `is_active` | boolean | Filter by active status |

**Success Response (200 OK):**
```json
[
  {
    "id": 1,
    "name": "Fall 2026",
    "is_active": true,
    "launch_open": true,
    "innovation_open": false,
    "created_at": "2026-03-05T10:00:00Z"
  }
]
```

---

### GET `/cycles/current/`

Get the current active cycle with toggle status.

**Auth Required:** Any authenticated user

**Success Response (200 OK):**
```json
{
  "id": 1,
  "name": "Fall 2026",
  "is_active": true,
  "launch_open": true,
  "innovation_open": false,
  "description": "Fall semester application cycle",
  "created_at": "2026-03-05T10:00:00Z",
  "updated_at": "2026-03-05T12:00:00Z"
}
```

**Error Responses:**
| Status | Reason |
|--------|--------|
| 404 | No active cycle exists |

---

### PATCH `/cycles/{cycle_id}/toggles/`

Update track toggles independently. Send only the toggles you want to change.

**Auth Required:** ADMIN only

**URL Params:** `cycle_id` — integer ID of the cycle

**Request Body (any combination):**
```json
{
  "launch_open": true
}
```

```json
{
  "innovation_open": true
}
```

```json
{
  "launch_open": true,
  "innovation_open": true
}
```

**Success Response (200 OK):**
```json
{
  "message": "Cycle toggles updated.",
  "cycle": {
    "id": 1,
    "name": "Fall 2026",
    "is_active": true,
    "launch_open": true,
    "innovation_open": false,
    ...
  }
}
```

**Key behavior:**
- Toggles are fully independent — opening one does not affect the other
- Toggles can be flipped on and off freely (reopening is allowed)
- Cannot toggle an inactive (closed) cycle

**Error Responses:**
| Status | Reason |
|--------|--------|
| 400 | No toggles provided, cycle is inactive |
| 403 | Not an admin |
| 404 | Cycle not found |

---

### POST `/cycles/{cycle_id}/close/`

Close the cycle permanently. Turns off all toggles and deactivates the cycle. Cannot be undone — create a new cycle for the next semester.

**Auth Required:** ADMIN only

**URL Params:** `cycle_id` — integer ID of the cycle

**Success Response (200 OK):**
```json
{
  "message": "Cycle 'Fall 2026' has been closed.",
  "cycle": {
    "id": 1,
    "name": "Fall 2026",
    "is_active": false,
    "launch_open": false,
    "innovation_open": false,
    ...
  }
}
```

**Error Responses:**
| Status | Reason |
|--------|--------|
| 400 | Cycle is already closed |
| 403 | Not an admin |
| 404 | Cycle not found |

---

### GET `/cycles/{cycle_id}/stats/`

Cycle statistics dashboard with user counts and GI completion data.

**Auth Required:** ADMIN or OPS_CHAIR

**URL Params:** `cycle_id` — integer ID of the cycle

**Success Response (200 OK):**
```json
{
  "cycle_id": 1,
  "cycle_name": "Fall 2026",
  "is_active": true,
  "launch_open": true,
  "innovation_open": false,
  "total_users": 50,
  "gi_completed": 35,
  "gi_pending": 15,
  "launch_apps": 0,
  "launch_assigned": 0,
  "innovation_proposals": 0,
  "innovation_assigned": 0,
  "unassigned_users": 15
}
```

Note: `launch_apps`, `launch_assigned`, `innovation_proposals`, `innovation_assigned` will be populated in Phase 3 & 4.

---

### POST `/auth/general-interest/`

Submit or update the General Interest form for the current active cycle.

If the student has already submitted a GI for the current cycle, this **updates** the existing form (upsert pattern). The GI form is always open during an active cycle — it is not gated by any toggle.

**Auth Required:** USER (student) only

**Request Body:**
```json
{
  "graduation_year": 2027,
  "college": "Khoury College of Computer Sciences",
  "major": "Computer Science",
  "skills": "Python, Django, React, SQL, Machine Learning",
  "interest_areas": "Engineering, Product Development, AI/ML",
  "why_join": "I want to gain real-world startup experience."
}
```

**Success Response — New Submission (201 Created):**
```json
{
  "message": "General Interest form submitted successfully.",
  "general_interest": {
    "id": 1,
    "user": 2,
    "user_email": "john.doe@northeastern.edu",
    "user_name": "John Doe",
    "cycle": 1,
    "cycle_name": "Fall 2026",
    "graduation_year": 2027,
    "college": "Khoury College of Computer Sciences",
    "major": "Computer Science",
    "skills": "Python, Django, React, SQL, Machine Learning",
    "interest_areas": "Engineering, Product Development, AI/ML",
    "why_join": "I want to gain real-world startup experience.",
    "submitted_at": "2026-03-05T14:00:00Z"
  }
}
```

**Success Response — Update (200 OK):**
```json
{
  "message": "General Interest form updated successfully.",
  "general_interest": { ... }
}
```

**Side effects:**
- First submission sets `user.is_gi_complete = true`
- Subsequent updates keep `is_gi_complete = true`

**Error Responses:**
| Status | Reason |
|--------|--------|
| 400 | Validation error (past graduation year, missing fields) |
| 403 | Not a student (Admin, Ops Chair, Launch Team cannot submit) |
| 404 | No active cycle exists |

---

### GET `/auth/general-interest/me/`

View the current user's GI submission for the active cycle.

**Auth Required:** Any authenticated user

**Success Response (200 OK):**
```json
{
  "id": 1,
  "user": 2,
  "user_email": "john.doe@northeastern.edu",
  "user_name": "John Doe",
  "cycle": 1,
  "cycle_name": "Fall 2026",
  "graduation_year": 2027,
  ...
}
```

**Error Responses:**
| Status | Reason |
|--------|--------|
| 404 | No GI submitted for current cycle, or no active cycle |

---

### GET `/audit/logs/`

View the audit trail with optional filters. Results are paginated.

**Auth Required:** ADMIN or OPS_CHAIR

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `action` | string | Filter by action type (e.g. `CYCLE_CREATED`, `GI_SUBMITTED`) |
| `actor_id` | integer | Filter by actor user ID |
| `target_type` | string | Filter by target type (e.g. `User`, `ApplicationCycle`) |

**Example:** `GET /audit/logs/?action=CYCLE_TOGGLES_UPDATED`

**Success Response (200 OK):**
```json
{
  "count": 15,
  "next": "http://127.0.0.1:8000/api/v1/audit/logs/?page=2",
  "previous": null,
  "results": [
    {
      "id": 5,
      "actor": 1,
      "actor_email": "admin@northeastern.edu",
      "action": "CYCLE_TOGGLES_UPDATED",
      "action_display": "Cycle Toggles Updated",
      "target_type": "ApplicationCycle",
      "target_id": 1,
      "metadata": {
        "cycle_name": "Fall 2026",
        "changes": {
          "launch_open": {"old": false, "new": true}
        }
      },
      "ip_address": "127.0.0.1",
      "created_at": "2026-03-05T12:00:00Z"
    }
  ]
}
```

**Audit Action Types:**
| Action | Triggered By |
|--------|-------------|
| `USER_REGISTERED` | Student self-registration |
| `LAUNCH_TEAM_CREATED` | Admin creates Launch Team account |
| `GI_SUBMITTED` | First GI form submission |
| `GI_UPDATED` | GI form update (resubmission) |
| `ROLE_CHANGED` | Admin changes a user's role |
| `PASSWORD_CHANGED` | User changes their password |
| `CYCLE_CREATED` | Admin creates a new cycle |
| `CYCLE_TOGGLES_UPDATED` | Admin updates track toggles |
| `CYCLE_CLOSED` | Admin closes a cycle |

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
| POST /cycles/ | ✅ | ❌ 403 | ❌ 403 | ❌ 403 | ❌ 401 |
| GET /cycles/list/ | ✅ | ✅ | ❌ 403 | ❌ 403 | ❌ 401 |
| GET /cycles/current/ | ✅ | ✅ | ✅ | ✅ | ❌ 401 |
| PATCH /cycles/{id}/toggles/ | ✅ | ❌ 403 | ❌ 403 | ❌ 403 | ❌ 401 |
| POST /cycles/{id}/close/ | ✅ | ❌ 403 | ❌ 403 | ❌ 403 | ❌ 401 |
| GET /cycles/{id}/stats/ | ✅ | ✅ | ❌ 403 | ❌ 403 | ❌ 401 |
| POST /auth/general-interest/ | ❌ 403 | ❌ 403 | ✅ | ❌ 403 | ❌ 401 |
| GET /auth/general-interest/me/ | ✅ | ✅ | ✅ | ✅ | ❌ 401 |
| GET /audit/logs/ | ✅ | ✅ | ❌ 403 | ❌ 403 | ❌ 401 |