# 🗄️ Database Schema

PostgreSQL 16 — Current state after Phase 1.

---

## Phase 1: Users Table

### DDL (what Django migrations actually create)

```sql
CREATE TABLE users (
    id                BIGSERIAL PRIMARY KEY,
    email             VARCHAR(254) NOT NULL UNIQUE,
    first_name        VARCHAR(150) NOT NULL,
    last_name         VARCHAR(150) NOT NULL,
    password          VARCHAR(128) NOT NULL,
    role              VARCHAR(20) NOT NULL DEFAULT 'USER',
    is_gi_complete    BOOLEAN NOT NULL DEFAULT FALSE,
    is_neu_email      BOOLEAN NOT NULL DEFAULT TRUE,
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,
    is_staff          BOOLEAN NOT NULL DEFAULT FALSE,
    is_superuser      BOOLEAN NOT NULL DEFAULT FALSE,
    last_login        TIMESTAMP WITH TIME ZONE,
    date_joined       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE UNIQUE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_role ON users (role);
CREATE INDEX idx_users_created_at ON users (created_at DESC);
```

### Column Details

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BIGSERIAL | PRIMARY KEY | Auto-incrementing. Used for all foreign keys. |
| `email` | VARCHAR(254) | NOT NULL, UNIQUE | Login identifier. Indexed for fast lookups. |
| `first_name` | VARCHAR(150) | NOT NULL | User's first name. |
| `last_name` | VARCHAR(150) | NOT NULL | User's last name. |
| `password` | VARCHAR(128) | NOT NULL | Hashed with PBKDF2-SHA256. Never stored as plaintext. |
| `role` | VARCHAR(20) | NOT NULL, DEFAULT 'USER' | One of: ADMIN, OPS_CHAIR, USER, LAUNCH_TEAM. |
| `is_gi_complete` | BOOLEAN | NOT NULL, DEFAULT FALSE | Set to TRUE when user submits General Interest form. |
| `is_neu_email` | BOOLEAN | NOT NULL, DEFAULT TRUE | FALSE only for LAUNCH_TEAM with non-NEU emails. |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | Soft delete / account disable. Django built-in. |
| `is_staff` | BOOLEAN | NOT NULL, DEFAULT FALSE | Access to Django Admin panel. TRUE for ADMINs. |
| `is_superuser` | BOOLEAN | NOT NULL, DEFAULT FALSE | Full Django permissions. Only for initial setup. |
| `last_login` | TIMESTAMPTZ | NULLABLE | Auto-updated by Django on each login. |
| `date_joined` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | From Django's AbstractUser. |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | From our TimestampMixin. Set once on creation. |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | From our TimestampMixin. Updated on every save. |

### Role Enum Values

```sql
-- Enforced at application level (Django TextChoices), not DB-level enum
-- Valid values for the role column:

'ADMIN'        -- Club leadership. Full platform control.
'OPS_CHAIR'    -- Operations team. Manages selections & assignments.
'USER'         -- Northeastern student. Applies & proposes.
'LAUNCH_TEAM'  -- External startup member. Reviews & selects candidates.
```

### Why BIGSERIAL PK Instead of UUID?

- University app with ~50 users/cycle, not a distributed system
- Integer PKs are faster for joins and indexes (8 bytes vs 16 bytes)
- Easier to debug: `user id 7` vs `user 550e8400-e29b-41d4-a716-446655440000`
- PostgreSQL handles sequential integers more efficiently than random UUIDs
- If we ever need public-facing IDs, we can add a separate `uuid` column without changing the PK

### Email Is NOT the PK

```
id = 1 (PK)              ← used for foreign keys, joins, internal references
email = "x@neu.edu"      ← used for login only (USERNAME_FIELD)
```

Email is the `USERNAME_FIELD` which tells Django "use this for authentication instead of username." The actual primary key is always `id`.

---

## Django Auto-Generated Tables

Django creates these automatically. We don't touch them directly:

```sql
-- Session management
CREATE TABLE django_session (...);

-- Admin action logging
CREATE TABLE django_admin_log (...);

-- Django's internal content type registry
CREATE TABLE django_content_type (...);

-- Django's built-in permissions (we use custom permission classes instead)
CREATE TABLE auth_permission (...);

-- JWT token blacklist (for refresh token rotation)
CREATE TABLE token_blacklist_blacklistedtoken (...);
CREATE TABLE token_blacklist_outstandingtoken (...);
```

---

## Full Schema — All 11 Tables (Planned)

Phase 1 implements only the `users` table. Here's the complete planned schema:

```sql
-- PHASE 1: FOUNDATION (DONE)

-- (users table shown above)


-- PHASE 2: CYCLES + GENERAL INTEREST + AUDIT

CREATE TABLE application_cycles (
    id             BIGSERIAL PRIMARY KEY,
    name           VARCHAR(100) NOT NULL,               -- e.g. "Fall 2026"
    phase          VARCHAR(40) NOT NULL DEFAULT 'SETUP', -- 8-state enum
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- phase values: SETUP → GI_OPEN → LAUNCH_APPS_OPEN → LAUNCH_SELECTION
--             → INNOVATION_PROPOSALS_OPEN → INNOVATION_APPS_OPEN
--             → INNOVATION_ASSIGNMENT → CLOSED

CREATE TABLE general_interests (
    id               BIGSERIAL PRIMARY KEY,
    user_id          BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    cycle_id         BIGINT NOT NULL REFERENCES application_cycles(id) ON DELETE CASCADE,
    graduation_year  INTEGER NOT NULL,
    college          VARCHAR(200) NOT NULL,
    major            VARCHAR(200) NOT NULL,
    skills           TEXT NOT NULL,
    interest_areas   TEXT NOT NULL,
    why_join         TEXT NOT NULL,
    submitted_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(user_id, cycle_id)  -- one GI per user per cycle
);

CREATE TABLE audit_logs (
    id             BIGSERIAL PRIMARY KEY,
    actor_id       BIGINT REFERENCES users(id) ON DELETE SET NULL,
    action         VARCHAR(50) NOT NULL,    -- e.g. 'USER_REGISTERED', 'ROLE_CHANGED'
    target_type    VARCHAR(50),             -- e.g. 'User', 'LaunchProject'
    target_id      BIGINT,
    metadata       JSONB,                   -- flexible extra data
    ip_address     INET,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_actor ON audit_logs(actor_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);


-- PHASE 3: LAUNCH TRACK

CREATE TABLE launch_projects (
    id             BIGSERIAL PRIMARY KEY,
    cycle_id       BIGINT NOT NULL REFERENCES application_cycles(id) ON DELETE CASCADE,
    team_id        BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title          VARCHAR(200) NOT NULL,
    description    TEXT NOT NULL,
    requirements   TEXT,
    max_members    INTEGER NOT NULL DEFAULT 4,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE launch_applications (
    id             BIGSERIAL PRIMARY KEY,
    user_id        BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id     BIGINT NOT NULL REFERENCES launch_projects(id) ON DELETE CASCADE,
    cycle_id       BIGINT NOT NULL REFERENCES application_cycles(id) ON DELETE CASCADE,
    resume_link    VARCHAR(500),
    portfolio_link VARCHAR(500),
    responses      JSONB,                    -- flexible Q&A responses
    status         VARCHAR(20) NOT NULL DEFAULT 'SUBMITTED',
    submitted_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(user_id, project_id, cycle_id)   -- one app per user per project
);

-- status values: SUBMITTED, FILTERED, SENT_TO_TEAM, SELECTED, NOT_SELECTED, WITHDRAWN

CREATE TABLE launch_candidates (
    id               BIGSERIAL PRIMARY KEY,
    application_id   BIGINT NOT NULL REFERENCES launch_applications(id) ON DELETE CASCADE,
    project_id       BIGINT NOT NULL REFERENCES launch_projects(id) ON DELETE CASCADE,
    sent_by_id       BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status           VARCHAR(20) NOT NULL DEFAULT 'PENDING_REVIEW',
    sent_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    selected_at      TIMESTAMPTZ,

    UNIQUE(application_id, project_id)
);

-- status values: PENDING_REVIEW, SELECTED, REJECTED


-- PHASE 4: INNOVATION TRACK

CREATE TABLE proposals (
    id             BIGSERIAL PRIMARY KEY,
    cycle_id       BIGINT NOT NULL REFERENCES application_cycles(id) ON DELETE CASCADE,
    proposer_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title          VARCHAR(200) NOT NULL,
    description    TEXT NOT NULL,
    tech_stack     TEXT,
    max_members    INTEGER NOT NULL DEFAULT 4,
    status         VARCHAR(20) NOT NULL DEFAULT 'SUBMITTED',
    submitted_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- status values: SUBMITTED, APPROVED, REJECTED

CREATE TABLE innovation_projects (
    id             BIGSERIAL PRIMARY KEY,
    proposal_id    BIGINT NOT NULL UNIQUE REFERENCES proposals(id) ON DELETE CASCADE,
    cycle_id       BIGINT NOT NULL REFERENCES application_cycles(id) ON DELETE CASCADE,
    lead_id        BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title          VARCHAR(200) NOT NULL,
    max_members    INTEGER NOT NULL DEFAULT 4,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE innovation_preferences (
    id             BIGSERIAL PRIMARY KEY,
    user_id        BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id     BIGINT NOT NULL REFERENCES innovation_projects(id) ON DELETE CASCADE,
    cycle_id       BIGINT NOT NULL REFERENCES application_cycles(id) ON DELETE CASCADE,
    rank           INTEGER NOT NULL CHECK (rank IN (1, 2, 3)),
    submitted_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(user_id, project_id, cycle_id),  -- can't rank same project twice
    UNIQUE(user_id, rank, cycle_id)         -- can't use same rank twice
);


-- PHASE 3-4: ASSIGNMENTS (shared by both tracks)

CREATE TABLE assignments (
    id                      BIGSERIAL PRIMARY KEY,
    user_id                 BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    cycle_id                BIGINT NOT NULL REFERENCES application_cycles(id) ON DELETE CASCADE,
    track                   VARCHAR(20) NOT NULL,  -- 'LAUNCH' or 'INNOVATION'
    launch_project_id       BIGINT REFERENCES launch_projects(id) ON DELETE SET NULL,
    innovation_project_id   BIGINT REFERENCES innovation_projects(id) ON DELETE SET NULL,
    assigned_by_id          BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assigned_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(user_id, cycle_id),  -- ONE assignment per user per cycle

    -- Exactly one project FK must be set
    CONSTRAINT chk_one_project CHECK (
        (launch_project_id IS NOT NULL AND innovation_project_id IS NULL)
        OR
        (launch_project_id IS NULL AND innovation_project_id IS NOT NULL)
    )
);
```

### Entity Relationship Diagram (Text)

```
users ──────────┬── 1:1 per cycle ──> general_interests
                │
                ├── 1:N ──> launch_applications
                │
                ├── 1:N ──> proposals
                │
                ├── 1:N (max 3) ──> innovation_preferences
                │
                ├── 1:1 per cycle ──> assignments  ⭐ (core constraint)
                │
                └── 1:N ──> audit_logs

application_cycles ──── 1:N ──> (all other tables reference cycle)

launch_projects ──── 1:N ──> launch_applications ──── 1:1 ──> launch_candidates

proposals ──── 1:1 ──> innovation_projects ──── 1:N ──> innovation_preferences
```

### The Core Constraint

The `assignments` table is the single source of truth:
- `UNIQUE(user_id, cycle_id)` = each student gets exactly ONE project per semester
- The CHECK constraint = assignment must be either Launch OR Innovation, never both
- When checking "is this user available?", query assignments — if a row exists, they're taken