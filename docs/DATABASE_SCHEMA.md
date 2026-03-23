# 🗄️ Database Schema

PostgreSQL 16 — Current state after Phase 3.

---

## Phase 1: Users Table

### DDL

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
'ADMIN'        -- Club leadership. Full platform control.
'OPS_CHAIR'    -- Operations team. Manages selections & assignments.
'USER'         -- Northeastern student. Applies & proposes.
'LAUNCH_TEAM'  -- External startup member. Reviews & selects candidates.
```

---

## Phase 2: Application Cycles

### DDL

```sql
CREATE TABLE application_cycles (
    id               BIGSERIAL PRIMARY KEY,
    name             VARCHAR(100) NOT NULL UNIQUE,
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    launch_open      BOOLEAN NOT NULL DEFAULT FALSE,
    innovation_open  BOOLEAN NOT NULL DEFAULT FALSE,
    description      TEXT NOT NULL DEFAULT '',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_cycles_is_active ON application_cycles (is_active);
CREATE INDEX idx_cycles_created_at ON application_cycles (created_at DESC);
```

### Toggle Design

The two toggles (`launch_open`, `innovation_open`) are fully independent:
- Admin can open/close each track at any time
- Both can be open simultaneously
- Closing one does not affect the other
- Toggles can be flipped on and off freely (reopening is allowed)
- Admin/Ops can assign students and manage projects regardless of toggle state
- Toggles only control what students can submit

---

## Phase 2: General Interests

### DDL

```sql
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
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_gi_per_user_per_cycle UNIQUE(user_id, cycle_id)
);
```

---

## Phase 2: Audit Logs

### DDL

```sql
CREATE TABLE audit_logs (
    id             BIGSERIAL PRIMARY KEY,
    actor_id       BIGINT REFERENCES users(id) ON DELETE SET NULL,
    action         VARCHAR(50) NOT NULL,
    target_type    VARCHAR(50) NOT NULL DEFAULT '',
    target_id      BIGINT,
    metadata       JSONB NOT NULL DEFAULT '{}',
    ip_address     INET,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_action_created ON audit_logs (action, created_at);
CREATE INDEX idx_audit_logs_actor_created ON audit_logs (actor_id, created_at);
CREATE INDEX idx_audit_logs_target ON audit_logs (target_type, target_id);
```

Audit logs are **append-only**. No updates or deletes are permitted.

### Action Values (Phase 1 + 2 + 3)

```sql
-- Phase 1: Accounts
'USER_REGISTERED'
'LAUNCH_TEAM_CREATED'
'ROLE_CHANGED'
'PASSWORD_CHANGED'

-- Phase 2: Cycles + GI
'GI_SUBMITTED'
'GI_UPDATED'
'CYCLE_CREATED'
'CYCLE_TOGGLES_UPDATED'
'CYCLE_CLOSED'

-- Phase 3: Launch Track
'LAUNCH_PROJECT_CREATED'
'LAUNCH_PROJECT_DELETED'
'LAUNCH_APPLICATION_SUBMITTED'
'LAUNCH_APPLICATION_FILTERED'
'LAUNCH_SENT_TO_TEAM'
'LAUNCH_CANDIDATE_SELECTED'
'LAUNCH_CANDIDATE_REJECTED'
```

---

## Phase 3: Launch Projects

### DDL

```sql
CREATE TABLE launch_projects (
    id             BIGSERIAL PRIMARY KEY,
    cycle_id       BIGINT NOT NULL REFERENCES application_cycles(id) ON DELETE CASCADE,
    team_id        BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title          VARCHAR(200) NOT NULL,
    description    TEXT NOT NULL,
    requirements   TEXT,
    max_members    INTEGER NOT NULL DEFAULT 4,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BIGSERIAL | PRIMARY KEY | Auto-incrementing. |
| `cycle_id` | BIGINT | FK → application_cycles, NOT NULL | The cycle this project belongs to. |
| `team_id` | BIGINT | FK → users, NOT NULL | The LAUNCH_TEAM user who owns this project. |
| `title` | VARCHAR(200) | NOT NULL | Project title. |
| `description` | TEXT | NOT NULL | Detailed description. |
| `requirements` | TEXT | NULLABLE | Skills or prerequisites. |
| `max_members` | INTEGER | NOT NULL, DEFAULT 4 | Maximum team size. |

---

## Phase 3: Launch Applications

### DDL

```sql
CREATE TABLE launch_applications (
    id             BIGSERIAL PRIMARY KEY,
    user_id        BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id     BIGINT NOT NULL REFERENCES launch_projects(id) ON DELETE CASCADE,
    cycle_id       BIGINT NOT NULL REFERENCES application_cycles(id) ON DELETE CASCADE,
    resume         VARCHAR(500),
    portfolio      VARCHAR(500),
    responses      JSONB,
    status         VARCHAR(20) NOT NULL DEFAULT 'SUBMITTED',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_la_per_user_per_project_per_cycle
        UNIQUE(user_id, project_id, cycle_id)
);
```

### Status Values

```sql
'SUBMITTED'       -- Student just applied
'FILTERED'        -- Admin/Ops marked as filtered
'SENT_TO_TEAM'    -- Forwarded to Launch Team for review
'SELECTED'        -- Launch Team selected → assignment created
'NOT_SELECTED'    -- Launch Team rejected
'WITHDRAWN'       -- Student withdrew (future feature)
```

### Status Flow

```
SUBMITTED → FILTERED → SENT_TO_TEAM → SELECTED / NOT_SELECTED
```

---

## Phase 3: Launch Candidates

### DDL

```sql
CREATE TABLE launch_candidates (
    id               BIGSERIAL PRIMARY KEY,
    application_id   BIGINT NOT NULL REFERENCES launch_applications(id) ON DELETE CASCADE,
    project_id       BIGINT NOT NULL REFERENCES launch_projects(id) ON DELETE CASCADE,
    status           VARCHAR(20) NOT NULL DEFAULT 'PENDING_REVIEW',
    selected_at      TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_lc_per_application_per_project
        UNIQUE(application_id, project_id)
);
```

### Status Values

```sql
'PENDING_REVIEW'  -- Sent to team, awaiting decision
'SELECTED'        -- Team selected → assignment auto-created
'REJECTED'        -- Team rejected
```

---

## Phase 3: Assignments

### DDL

```sql
CREATE TABLE assignments (
    id                                    BIGSERIAL PRIMARY KEY,
    user_id                               BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    cycle_id                              BIGINT NOT NULL REFERENCES application_cycles(id) ON DELETE CASCADE,
    track                                 VARCHAR(20) NOT NULL,
    launch_project_id                     BIGINT REFERENCES launch_projects(id) ON DELETE SET NULL,
    innovation_project_id_placeholder     BIGINT,
    assigned_by_id                        BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assigned_at                           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at                            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT one_assignment_per_user_per_cycle UNIQUE(user_id, cycle_id)
);
```

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `user_id` | BIGINT | FK → users, NOT NULL | The student assigned. |
| `cycle_id` | BIGINT | FK → application_cycles, NOT NULL | Which cycle. |
| `track` | VARCHAR(20) | NOT NULL | 'LAUNCH' or 'INNOVATION'. |
| `launch_project_id` | BIGINT | FK → launch_projects, NULLABLE | Set for Launch assignments. |
| `innovation_project_id_placeholder` | BIGINT | NULLABLE | Placeholder. Becomes FK in Phase 4. |
| `assigned_by_id` | BIGINT | FK → users, NOT NULL | Who made the assignment. |
| `assigned_at` | TIMESTAMPTZ | NOT NULL | When the assignment was made. |

### The Core Constraint

`UNIQUE(user_id, cycle_id)` = each student gets exactly ONE project per semester. When checking "is this user available?", query assignments — if a row exists, they're taken.

**Note:** The CHECK constraint enforcing exactly one of `launch_project` / `innovation_project` will be added in Phase 4 when `innovation_project_id_placeholder` becomes a proper FK.

---

## Django Auto-Generated Tables

Django creates these automatically. We don't touch them directly:

```sql
django_session                         -- Session management
django_admin_log                       -- Admin action logging
django_content_type                    -- Internal content type registry
auth_permission                        -- Built-in permissions
token_blacklist_blacklistedtoken       -- JWT blacklist
token_blacklist_outstandingtoken       -- JWT outstanding tokens
```

---

## Remaining Planned Schema (Phase 4)

```sql
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
-- status: SUBMITTED, APPROVED, REJECTED

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

    UNIQUE(user_id, project_id, cycle_id),
    UNIQUE(user_id, rank, cycle_id)
);
```

Phase 4 will also convert `assignments.innovation_project_id_placeholder` into a proper FK to `innovation_projects` and add the CHECK constraint ensuring exactly one project type is set.

---

## Entity Relationship Diagram

```
users ──────────┬── 1:1 per cycle ──> general_interests
                │
                ├── 1:N ──> launch_applications
                │
                ├── 1:N ──> proposals              (Phase 4)
                │
                ├── 1:N (max 3) ──> innovation_preferences  (Phase 4)
                │
                ├── 1:1 per cycle ──> assignments  ⭐ (core constraint)
                │
                └── 1:N ──> audit_logs

application_cycles ──── 1:N ──> (all other tables reference cycle)

launch_projects ──── 1:N ──> launch_applications ──── 1:1 ──> launch_candidates

proposals ──── 1:1 ──> innovation_projects ──── 1:N ──> innovation_preferences
```

---

## Design Decisions

### Why BIGSERIAL PK Instead of UUID?

- University app with ~50 users/cycle, not a distributed system
- Integer PKs are faster for joins and indexes (8 bytes vs 16 bytes)
- Easier to debug: `user id 7` vs `user 550e8400-e29b-41d4-a716-446655440000`
- PostgreSQL handles sequential integers more efficiently than random UUIDs
- If we ever need public-facing IDs, we can add a separate `uuid` column without changing the PK

### Why Independent Toggles Instead of Phase State Machine?

The original design used an 8-step linear state machine (SETUP → GI_OPEN → ... → CLOSED). This was replaced with independent toggles because:
- Admin needs to open/close tracks at any time, not in a fixed order
- Both tracks can run simultaneously
- Projects can be added anytime, not just during a specific phase
- Admin/Ops can assign students anytime after receiving applications
- The real workflow doesn't follow a strict linear progression

### Why a Placeholder Integer Instead of FK for Innovation?

The Assignment model references Innovation projects, but the Innovation app's models don't exist yet (Phase 4). Using a BigIntegerField placeholder avoids circular migration dependencies while keeping the data model forward-compatible. In Phase 4, this becomes a proper ForeignKey and the CHECK constraint is added.