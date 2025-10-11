-- ================== Config ==================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE SCHEMA IF NOT EXISTS reppy_dev;
SET search_path TO reppy_dev;

CREATE TYPE weekday_enum AS ENUM ('SUN','MON','TUE','WED','THU','FRI','SAT');
CREATE TYPE sentiment_enum AS ENUM ('POSITIVE','NEGATIVE','NEUTRAL');
CREATE TYPE sex_enum AS ENUM ('MALE','FEMALE','N/A');
CREATE TYPE unit_system_enum AS ENUM ('CM_KG','IN_LB');
CREATE TYPE sender_type_enum AS ENUM ('USER','REPPY');

-- ================== Users ==================

CREATE TABLE IF NOT EXISTS repy_user_l
(
    user_id    UUID PRIMARY KEY      DEFAULT gen_random_uuid(),
    username   VARCHAR(15)  NOT NULL UNIQUE,
    email      VARCHAR(100) NOT NULL UNIQUE,
    password   VARCHAR(200) NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS repy_user_bio_l
(
    user_id     UUID PRIMARY KEY REFERENCES repy_user_l ON DELETE CASCADE,
    sex         sex_enum    NOT NULL,
    height      FLOAT,
    body_weight FLOAT,
    birthdate   DATE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS repy_user_pref_l
(
    user_id        UUID PRIMARY KEY REFERENCES repy_user_l ON DELETE CASCADE,
    unit_system    unit_system_enum NOT NULL DEFAULT 'CM_KG',
    notif_reminder BOOLEAN          NOT NULL DEFAULT FALSE,
    locale         VARCHAR(10)      NOT NULL DEFAULT 'ko-KR',
    created_at     TIMESTAMPTZ      NOT NULL DEFAULT NOW()
);

-- ================== Equipments ==================

CREATE TABLE IF NOT EXISTS repy_equipment_m
(
    equipment_id UUID PRIMARY KEY     DEFAULT gen_random_uuid(),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS repy_equipment_i18n_m
(
    equipment_i18n_id UUID PRIMARY KEY      DEFAULT gen_random_uuid(),
    locale            VARCHAR(5)   NOT NULL,
    equipment_id      UUID         NOT NULL REFERENCES repy_equipment_m ON DELETE CASCADE,
    equipment_name    VARCHAR(200) NOT NULL,
    instruction       TEXT         NOT NULL,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS repy_user_equipment_map
(
    user_id      UUID        NOT NULL REFERENCES repy_user_l ON DELETE CASCADE,
    equipment_id UUID        NOT NULL REFERENCES repy_equipment_m ON DELETE CASCADE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, equipment_id)
);

-- ================== Exercises ==================

CREATE TABLE IF NOT EXISTS repy_muscle_m
(
    muscle_id  UUID PRIMARY KEY     DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS repy_muscle_i18n_m
(
    muscle_i18n_id UUID PRIMARY KEY     DEFAULT gen_random_uuid(),
    locale         VARCHAR(10) NOT NULL,
    muscle_id      UUID REFERENCES repy_muscle_m ON DELETE CASCADE,
    muscle_name    VARCHAR(30),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS repy_exercise_m
(
    exercise_id      UUID PRIMARY KEY     DEFAULT gen_random_uuid(),
    equipment_id     UUID        NOT NULL REFERENCES repy_equipment_m,
    main_muscle_id   UUID        NOT NULL REFERENCES repy_muscle_m,
    aux_muscle_id    UUID REFERENCES repy_muscle_m,
    difficulty_level SMALLINT    NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS repy_exercise_i18n_m
(
    exercise_i18n_id UUID PRIMARY KEY     DEFAULT gen_random_uuid(),
    locale           VARCHAR(10) NOT NULL,
    exercise_id      UUID        NOT NULL REFERENCES repy_exercise_m ON DELETE CASCADE,
    exercise_name    VARCHAR(60) NOT NULL,
    instruction      TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ================== Set Types (e.g., Warmup, Normal, Drop-set) ==================

CREATE TABLE IF NOT EXISTS repy_set_type_m
(
    set_type_id UUID PRIMARY KEY     DEFAULT gen_random_uuid(),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS repy_set_type_i18n_m
(
    set_type_i18n_id UUID PRIMARY KEY     DEFAULT gen_random_uuid(),
    locale           VARCHAR(10) NOT NULL,
    set_type_id      UUID        NOT NULL REFERENCES repy_set_type_m ON DELETE CASCADE,
    description      TEXT        NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ================== Programs, Routines ==================

CREATE TABLE IF NOT EXISTS repy_program_l
(
    program_id   UUID PRIMARY KEY     DEFAULT gen_random_uuid(),
    user_id      UUID        NOT NULL REFERENCES repy_user_l ON DELETE CASCADE,
    program_name TEXT        NOT NULL,
    start_date   TIMESTAMPTZ,
    goal_date    TIMESTAMPTZ,
    goal         TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS repy_routine_l
(
    routine_id    UUID PRIMARY KEY     DEFAULT gen_random_uuid(),
    user_id       UUID        NOT NULL REFERENCES repy_user_l ON DELETE CASCADE,
    routine_name  TEXT        NOT NULL,
    routine_order SMALLINT    NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS repy_routine_version_l
(
    routine_version_id UUID PRIMARY KEY     DEFAULT gen_random_uuid(),
    routine_id         UUID        NOT NULL REFERENCES repy_routine_l ON DELETE CASCADE,
    user_id            UUID        NOT NULL REFERENCES repy_user_l ON DELETE CASCADE,
    is_active          BOOLEAN     NOT NULL DEFAULT TRUE,
    memo               TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS repy_program_routine_map
(
    program_id UUID        NOT NULL REFERENCES repy_program_l ON DELETE CASCADE,
    routine_id UUID        NOT NULL REFERENCES repy_routine_l ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (program_id, routine_id)
);

-- ================== Workout Plans (Snapshot Hierarchy) ==================

CREATE TABLE IF NOT EXISTS repy_exercise_plan_l
(
    plan_id            UUID PRIMARY KEY     DEFAULT gen_random_uuid(),
    routine_version_id UUID        NOT NULL REFERENCES repy_routine_version_l ON DELETE CASCADE,
    exercise_id        UUID        NOT NULL REFERENCES repy_exercise_m,
    exec_order         SMALLINT    NOT NULL,
    memo               TEXT,
    description        TEXT        NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS repy_exercise_set_l
(
    set_id      UUID PRIMARY KEY     DEFAULT gen_random_uuid(),
    plan_id     UUID        NOT NULL REFERENCES repy_exercise_plan_l ON DELETE CASCADE,
    set_type_id UUID        NOT NULL REFERENCES repy_set_type_m,
    set_order   SMALLINT    NOT NULL,
    reps        INT,
    weight      FLOAT,
    rest_time   INT         NOT NULL, -- In seconds
    duration    INT,                  -- In seconds
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ================== Record & Feedback ==================

CREATE TABLE IF NOT EXISTS repy_workout_session_l
(
    session_id         UUID PRIMARY KEY     DEFAULT gen_random_uuid(),
    user_id            UUID        NOT NULL REFERENCES repy_user_l ON DELETE CASCADE,
    routine_version_id UUID        NOT NULL REFERENCES repy_routine_version_l,
    start_time         TIMESTAMPTZ NOT NULL,
    end_time           TIMESTAMPTZ NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS repy_set_record_l
(
    record_id        UUID PRIMARY KEY     DEFAULT gen_random_uuid(),
    session_id       UUID        NOT NULL REFERENCES repy_workout_session_l ON DELETE CASCADE,
    set_id           UUID        NOT NULL REFERENCES repy_exercise_set_l,
    actual_reps      INT,
    actual_weight    FLOAT,
    actual_rest_time INT,
    actual_duration  INT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS repy_feedback_l
(
    feedback_id   UUID PRIMARY KEY        DEFAULT gen_random_uuid(),
    user_id       UUID           NOT NULL REFERENCES repy_user_l ON DELETE CASCADE,
    session_id    UUID           NOT NULL REFERENCES repy_workout_session_l ON DELETE CASCADE,
    sentiment     sentiment_enum NOT NULL,
    feedback_text TEXT,
    created_at    TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

-- ================== Chat ==================

CREATE TABLE IF NOT EXISTS repy_chat_message_l
(
    message_id  UUID PRIMARY KEY          DEFAULT gen_random_uuid(),
    user_id     UUID             NOT NULL REFERENCES repy_user_l ON DELETE CASCADE,
    sender_type sender_type_enum NOT NULL,
    content     TEXT             NOT NULL,
    created_at  TIMESTAMPTZ      NOT NULL DEFAULT NOW()
);

-- ================== Indices ==================

CREATE UNIQUE INDEX IF NOT EXISTS routine_version_one_active_per_routine
    ON repy_routine_version_l (routine_id)
    WHERE is_active;
