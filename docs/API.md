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

---

## Phase 3 Endpoints (12 total)

### POST `/launch/projects/`

Create a new Launch Project for the active cycle. Projects can be created at any time — not gated by `launch_open`.

**Auth Required:** ADMIN only

**Request Body:**
```json
{
  "team_id": 2,
  "title": "AI Customer Support Bot",
  "description": "Build an AI-powered chatbot using LLMs.",
  "requirements": "Python, NLP, React",
  "max_members": 4
}
```

**Success Response (201 Created):**
```json
{
  "message": "Launch project created.",
  "project": {
    "id": 1,
    "cycle": 1,
    "team": 2,
    "team_name": "Rocket Labs",
    "team_email": "rocketlab@startup.com",
    "title": "AI Customer Support Bot",
    "description": "Build an AI-powered chatbot using LLMs.",
    "requirements": "Python, NLP, React",
    "max_members": 4,
    "application_count": 0,
    "created_at": "2026-03-19T20:00:00Z",
    "updated_at": "2026-03-19T20:00:00Z"
  }
}
```

**Business Rules:** `team_id` must reference a LAUNCH_TEAM user.

**Error Responses:**
| Status | Reason |
|--------|--------|
| 400 | team_id is not a LAUNCH_TEAM user, validation error |
| 403 | Not an admin |
| 404 | No active cycle, user not found |

---

### GET `/launch/projects/list/`

List all Launch projects for the active cycle.

**Auth Required:** Any authenticated user

---

### GET `/launch/projects/{project_id}/`

Get full details of a Launch project.

**Auth Required:** Any authenticated user

---

### DELETE `/launch/projects/{project_id}/`

Delete a Launch project.

**Auth Required:** ADMIN only

**Business Rules:** Cannot delete if any candidate has been SELECTED (assignment exists).

---

### POST `/launch/projects/{project_id}/apply/`

Student applies to a Launch Project.

**Auth Required:** USER with `is_gi_complete=True`

**Request Body:**
```json
{
  "resume": "https://drive.google.com/my-resume",
  "portfolio": "https://github.com/username",
  "responses": {
    "motivation": "I love building AI products",
    "availability": "20 hours/week"
  }
}
```

**Business Rules:**
- `launch_open` must be True on the active cycle
- Student must have completed GI form
- No duplicate application to the same project in the same cycle
- Student must not already be assigned this cycle

---

### GET `/launch/projects/{project_id}/applicants/`

View all applicants for a specific project.

**Auth Required:** ADMIN or OPS_CHAIR

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `status` | string | Filter by status: SUBMITTED, FILTERED, SENT_TO_TEAM, SELECTED, NOT_SELECTED |

---

### POST `/launch/applications/filter/`

Bulk mark applications as FILTERED.

**Auth Required:** ADMIN or OPS_CHAIR

**Request Body:**
```json
{
  "application_ids": [1, 2, 3]
}
```

**Business Rules:** Only SUBMITTED applications can be filtered.

---

### POST `/launch/applications/send-to-team/`

Send filtered applications to the Launch Team for review. Creates LaunchCandidate records and updates application status to SENT_TO_TEAM.

**Auth Required:** ADMIN or OPS_CHAIR

**Request Body:**
```json
{
  "application_ids": [1, 2]
}
```

**Business Rules:** Only FILTERED applications can be sent. Cannot double-send.

---

### GET `/launch/my-applications/`

View own Launch applications for the current cycle.

**Auth Required:** USER (student) only

---

### GET `/launch/candidates/`

View candidates sent to this Launch Team member's projects. Only shows candidates for projects the team member owns.

**Auth Required:** LAUNCH_TEAM only

---

### POST `/launch/candidates/{candidate_id}/select/`

Launch Team selects a candidate. Auto-creates an Assignment record (track=LAUNCH).

**Auth Required:** LAUNCH_TEAM only

**Business Rules:**
- Only PENDING_REVIEW candidates can be selected
- Launch Team can only select candidates for their own projects
- Blocks if student already has a Launch assignment (409 Conflict)
- Launch takes priority over Innovation assignments

If the student has an Innovation assignment, it is replaced and a warning is returned.

---

### POST `/launch/candidates/{candidate_id}/reject/`

Launch Team rejects a candidate.

**Auth Required:** LAUNCH_TEAM only

**Business Rules:** Only PENDING_REVIEW candidates can be rejected. Sets candidate status to REJECTED and application status to NOT_SELECTED.

---

### Launch Application Status Flow

```
SUBMITTED
    │
    ▼ (Admin/Ops filters)
FILTERED
    │
    ▼ (Admin/Ops sends to team)
SENT_TO_TEAM
    │
    ├──▶ SELECTED      (Launch Team selects → Assignment created)
    │
    ├──▶ NOT_SELECTED   (Launch Team rejects)
    │
    └──▶ WITHDRAWN      (Student withdraws — future feature)
```

---

## Phase 4 Endpoints (11 total)

### POST `/innovation/proposals/`

Student submits an Innovation proposal for the current cycle.

**Auth Required:** USER with `is_gi_complete=True`

**Request Body:**
```json
{
  "title": "AI-Powered Campus Navigator",
  "description": "A mobile app that uses AR to help students navigate campus buildings.",
  "tech_stack": "React Native, Python, ARKit",
  "max_members": 5
}
```

**Success Response (201 Created):**
```json
{
  "message": "Proposal submitted successfully.",
  "proposal": {
    "id": 1,
    "title": "AI-Powered Campus Navigator",
    "description": "A mobile app that uses AR to help students navigate campus buildings.",
    "tech_stack": "React Native, Python, ARKit",
    "max_members": 5,
    "status": "SUBMITTED",
    "status_display": "Submitted",
    "submitted_at": "2026-03-25T20:00:00Z"
  }
}
```

**Business Rules:**
- `innovation_open` must be True on the active cycle
- GI must be complete
- One proposal per student per cycle
- Student must not already be assigned this cycle

**Error Responses:**
| Status | Reason |
|--------|--------|
| 400 | Innovation closed, already assigned, validation error |
| 403 | Not a student, GI not complete |
| 404 | No active cycle |
| 409 | Already submitted a proposal this cycle |

---

### GET `/innovation/proposals/list/`

List all proposals for the active cycle. Supports status filtering.

**Auth Required:** ADMIN or OPS_CHAIR

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `status` | string | Filter by: SUBMITTED, APPROVED, REJECTED |

**Success Response (200 OK):**
```json
[
  {
    "id": 1,
    "cycle": 1,
    "proposer": 4,
    "proposer_name": "Alice Johnson",
    "proposer_email": "alice@northeastern.edu",
    "title": "AI-Powered Campus Navigator",
    "description": "A mobile app...",
    "tech_stack": "React Native, Python, ARKit",
    "max_members": 5,
    "status": "SUBMITTED",
    "status_display": "Submitted",
    "submitted_at": "2026-03-25T20:00:00Z"
  }
]
```

---

### GET `/innovation/my-proposal/`

Student views their own proposal for the current cycle.

**Auth Required:** USER (student) only

**Success Response (200 OK):** Same shape as the `proposal` field in the submit response.

**Error Responses:**
| Status | Reason |
|--------|--------|
| 404 | No proposal found for the current cycle |

---

### POST `/innovation/proposals/{proposal_id}/approve/`

Admin/Ops approves a proposal. Creates an InnovationProject with the proposer as project lead.

**Auth Required:** ADMIN or OPS_CHAIR

**Success Response (200 OK):**
```json
{
  "message": "Proposal approved. Innovation project created.",
  "proposal": {
    "id": 1,
    "status": "APPROVED",
    "proposer_name": "Alice Johnson",
    "proposer_email": "alice@northeastern.edu",
    ...
  },
  "project": {
    "id": 1,
    "proposal_id": 1,
    "cycle": 1,
    "title": "AI-Powered Campus Navigator",
    "lead": 4,
    "lead_name": "Alice Johnson",
    "lead_email": "alice@northeastern.edu",
    "max_members": 5,
    "preference_count": 0,
    "assigned_count": 0,
    "created_at": "2026-03-25T20:30:00Z"
  }
}
```

**Business Rules:**
- Only SUBMITTED proposals can be approved
- Does NOT auto-assign the proposer (assignment happens separately)
- Proposer becomes the project lead on the InnovationProject record

**Error Responses:**
| Status | Reason |
|--------|--------|
| 400 | Proposal is not in SUBMITTED status |
| 403 | Not Admin/Ops |
| 404 | Proposal not found |

---

### POST `/innovation/proposals/{proposal_id}/reject/`

Admin/Ops rejects a proposal. After rejection, the proposer becomes eligible to submit preferences.

**Auth Required:** ADMIN or OPS_CHAIR

**Success Response (200 OK):**
```json
{
  "message": "Proposal rejected.",
  "proposal": {
    "id": 1,
    "status": "REJECTED",
    ...
  }
}
```

**Business Rules:** Only SUBMITTED proposals can be rejected.

**Error Responses:**
| Status | Reason |
|--------|--------|
| 400 | Proposal is not in SUBMITTED status |
| 403 | Not Admin/Ops |
| 404 | Proposal not found |

---

### GET `/innovation/projects/`

List all approved Innovation projects for the active cycle.

**Auth Required:** Any authenticated user

**Success Response (200 OK):**
```json
[
  {
    "id": 1,
    "title": "AI-Powered Campus Navigator",
    "lead": 4,
    "lead_name": "Alice Johnson",
    "lead_email": "alice@northeastern.edu",
    "max_members": 5,
    "preference_count": 3,
    "assigned_count": 1,
    "created_at": "2026-03-25T20:30:00Z"
  }
]
```

---

### GET `/innovation/projects/{project_id}/`

Get full detail of an Innovation project.

**Auth Required:** Any authenticated user

**Success Response (200 OK):**
```json
{
  "id": 1,
  "proposal_id": 1,
  "cycle": 1,
  "title": "AI-Powered Campus Navigator",
  "lead": 4,
  "lead_name": "Alice Johnson",
  "lead_email": "alice@northeastern.edu",
  "max_members": 5,
  "preference_count": 3,
  "assigned_count": 1,
  "created_at": "2026-03-25T20:30:00Z"
}
```

---

### POST `/innovation/preferences/`

Student submits ranked preferences for Innovation projects (1-3 projects).

**Auth Required:** USER with `is_gi_complete=True`

**Request Body:**
```json
{
  "preferences": [
    {"project_id": 1, "rank": 1},
    {"project_id": 3, "rank": 2},
    {"project_id": 5, "rank": 3}
  ]
}
```

**Success Response (201 Created):**
```json
{
  "message": "Preferences submitted successfully.",
  "preferences": [
    {"id": 1, "project": 1, "project_title": "AI Navigator", "rank": 1, "submitted_at": "..."},
    {"id": 2, "project": 3, "project_title": "FinTech App", "rank": 2, "submitted_at": "..."},
    {"id": 3, "project": 5, "project_title": "Health Tracker", "rank": 3, "submitted_at": "..."}
  ]
}
```

**Business Rules:**
- `innovation_open` must be True
- GI must be complete
- Student must NOT be already assigned this cycle
- Student must NOT have a pending (SUBMITTED) or approved proposal
- Rejected proposal is OK — they rejoin the pool
- Max 3 preferences, unique ranks (1, 2, 3), unique projects
- Replaces existing preferences (upsert pattern)

**Error Responses:**
| Status | Reason |
|--------|--------|
| 400 | Innovation closed, already assigned, active proposal, validation errors |
| 403 | Not a student, GI not complete |
| 404 | Project not found in current cycle |

---

### PUT `/innovation/preferences/`

Update preferences. Same logic as POST — replaces existing.

**Auth Required:** USER with `is_gi_complete=True`

**Request Body:** Same as POST.

**Success Response (200 OK):** Same shape as POST response.

---

### GET `/innovation/my-preferences/`

View own Innovation preferences for the current cycle.

**Auth Required:** USER (student) only

**Success Response (200 OK):**
```json
[
  {"id": 1, "project": 1, "project_title": "AI Navigator", "rank": 1, "submitted_at": "..."},
  {"id": 2, "project": 3, "project_title": "FinTech App", "rank": 2, "submitted_at": "..."}
]
```

---

### GET `/innovation/projects/{project_id}/preferences/`

Admin/Ops views all students who ranked this project, with rank breakdown.

**Auth Required:** ADMIN or OPS_CHAIR

**Success Response (200 OK):**
```json
[
  {
    "id": 1,
    "user": 5,
    "user_name": "Bob Smith",
    "user_email": "bob@northeastern.edu",
    "project": 1,
    "project_title": "AI Navigator",
    "rank": 1,
    "submitted_at": "2026-03-25T21:00:00Z"
  },
  {
    "id": 4,
    "user": 7,
    "user_name": "Carol Lee",
    "user_email": "carol@northeastern.edu",
    "project": 1,
    "project_title": "AI Navigator",
    "rank": 2,
    "submitted_at": "2026-03-25T21:30:00Z"
  }
]
```

---

### POST `/innovation/assign/`

Admin/Ops assigns a student to an Innovation project. Not gated by `innovation_open` toggle.

**Auth Required:** ADMIN or OPS_CHAIR

**Request Body:**
```json
{
  "user_id": 5,
  "project_id": 1
}
```

**Success Response (201 Created):**
```json
{
  "message": "Student assigned to Innovation project.",
  "assignment_id": 3,
  "student_email": "bob@northeastern.edu",
  "project_title": "AI-Powered Campus Navigator",
  "track": "INNOVATION"
}
```

**Business Rules:**
- Student must exist and be a USER role
- Project must exist in the current cycle
- Student must NOT already be assigned (Launch or Innovation)
- Team capacity check (max_members)

**Error Responses:**
| Status | Reason |
|--------|--------|
| 400 | Not a student, team full, validation error |
| 403 | Not Admin/Ops |
| 404 | User or project not found |
| 409 | Student already assigned this cycle |

---

### Innovation Proposal Status Flow

```
SUBMITTED
    │
    ├──▶ APPROVED   (Admin/Ops approves → InnovationProject created)
    │                 Proposer = project lead
    │                 Proposer blocked from preferences
    │
    └──▶ REJECTED   (Admin/Ops rejects)
                      Proposer can now submit preferences
```

### Innovation Preference Eligibility

```
Can submit preferences if ALL of:
  ✅ GI complete
  ✅ innovation_open = True
  ✅ Not assigned to any project (Launch or Innovation)
  ✅ No SUBMITTED or APPROVED proposal this cycle
  ✅ (REJECTED proposal is OK — they rejoin the pool)
```

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
| POST /launch/projects/ | ✅ | ❌ 403 | ❌ 403 | ❌ 403 | ❌ 401 |
| GET /launch/projects/list/ | ✅ | ✅ | ✅ | ✅ | ❌ 401 |
| GET /launch/projects/{id}/ | ✅ | ✅ | ✅ | ✅ | ❌ 401 |
| DELETE /launch/projects/{id}/ | ✅ | ❌ 403 | ❌ 403 | ❌ 403 | ❌ 401 |
| POST /launch/projects/{id}/apply/ | ❌ 403 | ❌ 403 | ✅ (GI) | ❌ 403 | ❌ 401 |
| GET /launch/projects/{id}/applicants/ | ✅ | ✅ | ❌ 403 | ❌ 403 | ❌ 401 |
| POST /launch/applications/filter/ | ✅ | ✅ | ❌ 403 | ❌ 403 | ❌ 401 |
| POST /launch/applications/send-to-team/ | ✅ | ✅ | ❌ 403 | ❌ 403 | ❌ 401 |
| GET /launch/my-applications/ | ❌ 403 | ❌ 403 | ✅ | ❌ 403 | ❌ 401 |
| GET /launch/candidates/ | ❌ 403 | ❌ 403 | ❌ 403 | ✅ | ❌ 401 |
| POST /launch/candidates/{id}/select/ | ❌ 403 | ❌ 403 | ❌ 403 | ✅ | ❌ 401 |
| POST /launch/candidates/{id}/reject/ | ❌ 403 | ❌ 403 | ❌ 403 | ✅ | ❌ 401 |
| POST /innovation/proposals/ | ❌ 403 | ❌ 403 | ✅ (GI) | ❌ 403 | ❌ 401 |
| GET /innovation/proposals/list/ | ✅ | ✅ | ❌ 403 | ❌ 403 | ❌ 401 |
| GET /innovation/my-proposal/ | ❌ 403 | ❌ 403 | ✅ | ❌ 403 | ❌ 401 |
| POST /innovation/proposals/{id}/approve/ | ✅ | ✅ | ❌ 403 | ❌ 403 | ❌ 401 |
| POST /innovation/proposals/{id}/reject/ | ✅ | ✅ | ❌ 403 | ❌ 403 | ❌ 401 |
| GET /innovation/projects/ | ✅ | ✅ | ✅ | ✅ | ❌ 401 |
| GET /innovation/projects/{id}/ | ✅ | ✅ | ✅ | ✅ | ❌ 401 |
| POST /innovation/preferences/ | ❌ 403 | ❌ 403 | ✅ (GI) | ❌ 403 | ❌ 401 |
| PUT /innovation/preferences/ | ❌ 403 | ❌ 403 | ✅ (GI) | ❌ 403 | ❌ 401 |
| GET /innovation/my-preferences/ | ❌ 403 | ❌ 403 | ✅ | ❌ 403 | ❌ 401 |
| GET /innovation/projects/{id}/preferences/ | ✅ | ✅ | ❌ 403 | ❌ 403 | ❌ 401 |
| POST /innovation/assign/ | ✅ | ✅ | ❌ 403 | ❌ 403 | ❌ 401 |

## Audit Action Types

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
| `LAUNCH_PROJECT_CREATED` | Admin creates a Launch project |
| `LAUNCH_PROJECT_DELETED` | Admin deletes a Launch project |
| `LAUNCH_APPLICATION_SUBMITTED` | Student applies to a Launch project |
| `LAUNCH_APPLICATION_FILTERED` | Admin/Ops filters an application |
| `LAUNCH_SENT_TO_TEAM` | Admin/Ops sends candidate to Launch Team |
| `LAUNCH_CANDIDATE_SELECTED` | Launch Team selects a candidate |
| `LAUNCH_CANDIDATE_REJECTED` | Launch Team rejects a candidate |
| `PROPOSAL_SUBMITTED` | Student submits an Innovation proposal |
| `PROPOSAL_APPROVED` | Admin/Ops approves a proposal |
| `PROPOSAL_REJECTED` | Admin/Ops rejects a proposal |
| `INNOVATION_PROJECT_DELETED` | Admin deletes an Innovation project |
| `PREFERENCES_SUBMITTED` | Student submits/updates preferences |
| `INNOVATION_ASSIGNED` | Admin/Ops assigns student to Innovation project |
| `ASSIGNMENT_REMOVED` | Admin removes an assignment (Phase 5) |