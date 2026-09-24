-- Admission Lead Management: PostgreSQL schema
-- Status values and roles use TEXT + CHECK (easier to change than ENUM types).

CREATE TABLE users (
    id        SERIAL PRIMARY KEY,
    name      TEXT NOT NULL,
    role      TEXT NOT NULL CHECK (role IN ('counsellor', 'manager')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE lead_sources (
    id   SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE courses (
    id   SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE leads (
    id               SERIAL PRIMARY KEY,
    name             TEXT NOT NULL,
    phone            TEXT NOT NULL,                 -- as entered
    phone_normalized TEXT NOT NULL UNIQUE,          -- last 10 digits; catches duplicates
    email            TEXT,
    source_id        INT NOT NULL REFERENCES lead_sources(id),
    status           TEXT NOT NULL DEFAULT 'new'
        CHECK (status IN ('new', 'contacted', 'interested', 'follow_up',
                          'applied', 'converted', 'lost')),
    lost_reason      TEXT,
    assigned_to      INT REFERENCES users(id),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (status <> 'lost' OR lost_reason IS NOT NULL)
);

-- A lead can be interested in more than one course
CREATE TABLE lead_courses (
    lead_id   INT NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    course_id INT NOT NULL REFERENCES courses(id),
    priority  INT NOT NULL DEFAULT 1,               -- 1 = first choice
    PRIMARY KEY (lead_id, course_id)
);

-- "Overdue" is computed (status = 'pending' AND due_at < now()), so no cron job is needed.
CREATE TABLE follow_ups (
    id           SERIAL PRIMARY KEY,
    lead_id      INT NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    due_at       TIMESTAMPTZ NOT NULL,
    type         TEXT NOT NULL CHECK (type IN ('call', 'whatsapp', 'visit', 'email')),
    note         TEXT,
    status       TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'done', 'cancelled')),
    created_by   INT REFERENCES users(id),
    completed_at TIMESTAMPTZ
);

-- Audit trail: one row per status change, reassignment, follow-up event, or note
CREATE TABLE lead_activities (
    id         SERIAL PRIMARY KEY,
    lead_id    INT NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    actor_id   INT REFERENCES users(id),            -- NULL = system
    action     TEXT NOT NULL,                       -- created, status_changed, reassigned, follow_up_added, ...
    old_value  TEXT,
    new_value  TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_leads_status      ON leads(status);
CREATE INDEX idx_leads_assigned_to ON leads(assigned_to);
CREATE INDEX idx_leads_source      ON leads(source_id);
CREATE INDEX idx_leads_last_activity ON leads(last_activity_at);
CREATE INDEX idx_followups_pending_due ON follow_ups(due_at) WHERE status = 'pending';
CREATE INDEX idx_activities_lead   ON lead_activities(lead_id, created_at);

-- Seed data
INSERT INTO users (name, role) VALUES
    ('Meera Kulkarni', 'manager'),
    ('Rohan Patil',    'counsellor'),
    ('Sneha Joshi',    'counsellor'),
    ('Aditya More',    'counsellor');

INSERT INTO lead_sources (name) VALUES
    ('Website'), ('Walk-in'), ('Phone call'), ('WhatsApp'), ('Education fair'), ('Campaign');

INSERT INTO courses (name) VALUES
    ('B.Tech Computer Science'), ('B.Tech Mechanical'), ('BBA'), ('MBA'), ('B.Com');
