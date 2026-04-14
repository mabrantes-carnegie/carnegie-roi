-- ============================================================
-- QUERY 3: Geography Breakdown — City Grain
-- Grain: institution × term_year × term_semester × state × city
-- Export as: q3_geography.csv
-- ============================================================
WITH base AS (
    SELECT
        c.person_id,
        c.application_id,
        c.institution_id,
        -- Address
        a.region    AS student_state,
        a.city      AS student_city,
        -- Stage dates
        c.person_inquired_date,
        c.app_created_date,
        c.app_type,
        c.app_submitted_date,
        c.app_admitted_date,
        c.app_deposited_date,
        c.app_enrolled_date,
        c.app_exit_date,
        c.app_exit_after_deposit,
        -- Person-first fields (Prospect, Inquiry)
        COALESCE(c.person_student_type,        c.app_student_type)        AS person_student_type,
        COALESCE(c.person_entry_term_year,     c.app_entry_term_year)     AS person_term_year,
        COALESCE(c.person_entry_term_semester, c.app_entry_term_semester) AS person_term_semester,
        -- App-first fields (App stages, Deposits, Enrolled)
        COALESCE(c.app_student_type,        c.person_student_type)        AS app_student_type,
        COALESCE(c.app_entry_term_year,     c.person_entry_term_year)     AS app_term_year,
        COALESCE(c.app_entry_term_semester, c.person_entry_term_semester) AS app_term_semester
    FROM `unified-data-platform-prod.udp_url.conversion` AS c
    INNER JOIN `unified-data-platform-prod.udp_udl.institution` AS i
        ON i.id = c.institution_id
    LEFT JOIN `unified-data-platform-prod.udp_udl.address` AS a
        ON  a.person_id      = c.person_id
        AND a.institution_id = c.institution_id
        AND a.address_rank   = 1
    WHERE i.name = 'Central Washington University'
        AND c.person_is_international_student = FALSE
),

-- Inquiries: person-level stage
inquiries AS (
    SELECT
        student_state, student_city, person_term_year AS term_year, person_term_semester AS term_semester,
        COUNT(DISTINCT person_id) AS total_inquiries
    FROM base
    WHERE person_inquired_date IS NOT NULL
        AND person_term_year     IN (2024, 2025, 2026)
        AND person_term_semester = 'Fall'
    GROUP BY 1, 2, 3, 4
),

-- App Starts: app-level stage
app_starts AS (
    SELECT
        student_state, student_city, app_term_year AS term_year, app_term_semester AS term_semester,
        COUNT(DISTINCT application_id) AS total_app_starts
    FROM base
    WHERE CASE
            WHEN LOWER(app_type) LIKE '%common%' THEN app_submitted_date
            ELSE app_created_date
          END IS NOT NULL
        AND app_term_year     IN (2024, 2025, 2026)
        AND app_term_semester = 'Fall'
    GROUP BY 1, 2, 3, 4
),

-- App Submits: app-level stage
app_submits AS (
    SELECT
        student_state, student_city, app_term_year AS term_year, app_term_semester AS term_semester,
        COUNT(DISTINCT application_id) AS total_app_submits
    FROM base
    WHERE app_submitted_date IS NOT NULL
        AND app_term_year     IN (2024, 2025, 2026)
        AND app_term_semester = 'Fall'
    GROUP BY 1, 2, 3, 4
),

-- Admits: app-level stage
admits AS (
    SELECT
        student_state, student_city, app_term_year AS term_year, app_term_semester AS term_semester,
        COUNT(DISTINCT application_id) AS total_admits
    FROM base
    WHERE app_admitted_date IS NOT NULL
        AND app_term_year     IN (2024, 2025, 2026)
        AND app_term_semester = 'Fall'
    GROUP BY 1, 2, 3, 4
),

-- Deposits: app-level stage (person_id for dedup)
deposits AS (
    SELECT
        student_state, student_city, app_term_year AS term_year, app_term_semester AS term_semester,
        COUNT(DISTINCT person_id)    AS total_deposits,
        COUNT(DISTINCT CASE
            WHEN app_exit_date IS NOT NULL
            AND app_exit_after_deposit = TRUE
            THEN person_id END)      AS total_exits_after_deposit
    FROM base
    WHERE app_deposited_date IS NOT NULL
        AND app_term_year     IN (2024, 2025, 2026)
        AND app_term_semester = 'Fall'
    GROUP BY 1, 2, 3, 4
),

-- Enrolled: app-level stage (person_id for dedup)
enrolled AS (
    SELECT
        student_state, student_city, app_term_year AS term_year, app_term_semester AS term_semester,
        COUNT(DISTINCT person_id) AS total_enrolled
    FROM base
    WHERE app_enrolled_date IS NOT NULL
        AND app_term_year     IN (2024, 2025, 2026)
        AND app_term_semester = 'Fall'
    GROUP BY 1, 2, 3, 4
),

-- All combinations of state × city × term_year × term_semester
all_keys AS (
    SELECT student_state, student_city, term_year, term_semester FROM inquiries
    UNION DISTINCT
    SELECT student_state, student_city, term_year, term_semester FROM app_starts
    UNION DISTINCT
    SELECT student_state, student_city, term_year, term_semester FROM app_submits
    UNION DISTINCT
    SELECT student_state, student_city, term_year, term_semester FROM admits
    UNION DISTINCT
    SELECT student_state, student_city, term_year, term_semester FROM deposits
    UNION DISTINCT
    SELECT student_state, student_city, term_year, term_semester FROM enrolled
)

SELECT
    'Central Washington University'             AS institution_name,
    'WA'                                        AS institution_state,
    k.student_state,
    k.student_city,
    k.term_year,
    k.term_semester,
    COALESCE(inq.total_inquiries,    0)         AS total_inquiries,
    COALESCE(ast.total_app_starts,   0)         AS total_app_starts,
    COALESCE(sub.total_app_submits,  0)         AS total_app_submits,
    COALESCE(adm.total_admits,       0)         AS total_admits,
    COALESCE(dep.total_deposits,     0)         AS total_deposits,
    COALESCE(dep.total_deposits,     0)
        - COALESCE(dep.total_exits_after_deposit, 0) AS total_net_deposits,
    COALESCE(enr.total_enrolled,     0)         AS total_enrolled
FROM all_keys AS k
LEFT JOIN inquiries  AS inq ON inq.student_state = k.student_state AND inq.student_city = k.student_city AND inq.term_year = k.term_year AND inq.term_semester = k.term_semester
LEFT JOIN app_starts AS ast ON ast.student_state = k.student_state AND ast.student_city = k.student_city AND ast.term_year = k.term_year AND ast.term_semester = k.term_semester
LEFT JOIN app_submits AS sub ON sub.student_state = k.student_state AND sub.student_city = k.student_city AND sub.term_year = k.term_year AND sub.term_semester = k.term_semester
LEFT JOIN admits     AS adm ON adm.student_state = k.student_state AND adm.student_city = k.student_city AND adm.term_year = k.term_year AND adm.term_semester = k.term_semester
LEFT JOIN deposits   AS dep ON dep.student_state = k.student_state AND dep.student_city = k.student_city AND dep.term_year = k.term_year AND dep.term_semester = k.term_semester
LEFT JOIN enrolled   AS enr ON enr.student_state = k.student_state AND enr.student_city = k.student_city AND enr.term_year = k.term_year AND enr.term_semester = k.term_semester
ORDER BY total_inquiries DESC