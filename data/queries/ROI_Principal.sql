-- ============================================================
-- QUERY 6: Single Data Source for Entire Dashboard
-- Export as: q6_fbc_monthly.csv
-- VALIDATED: When aggregated without program_name, matches
-- funnel_benchmark_current 100% across all stages.
-- When grouped by program_name, provides per-program rankings.
-- Inquiries grouped by program may show a student in multiple
-- programs if they applied to more than one — this is expected
-- and correct for program-level analysis. The dashboard does NOT
-- show a program-level total that could be compared with
-- institution-level KPIs.
-- ============================================================

WITH conversion_unpivoted AS (
    SELECT
        conv.institution_id,
        conv.person_id,
        conv.application_id,
        CASE
            WHEN stage.funnel_stage_for_day IN ('Prospect', 'Inquiry')
            THEN COALESCE(conv.person_entry_term_year, conv.app_entry_term_year)
            ELSE COALESCE(conv.app_entry_term_year, conv.person_entry_term_year)
        END AS entry_term_year,
        CASE
            WHEN stage.funnel_stage_for_day IN ('Prospect', 'Inquiry')
            THEN COALESCE(conv.person_entry_term_semester, conv.app_entry_term_semester)
            ELSE COALESCE(conv.app_entry_term_semester, conv.person_entry_term_semester)
        END AS entry_term_semester,
        CASE
            WHEN stage.funnel_stage_for_day IN ('Prospect', 'Inquiry')
            THEN COALESCE(conv.person_student_type, conv.app_student_type)
            ELSE COALESCE(conv.app_student_type, conv.person_student_type)
        END AS student_type,
        DATE(stage.funnel_day) AS funnel_day,
        stage.funnel_stage_for_day,
        conv.person_is_stealth_inquiry,
        conv.person_is_stealth_app,
        conv.person_prospect_date,
        conv.person_inquired_date,
        conv.app_submitted_date,
        conv.app_deposited_date,
        conv.app_exit_after_deposit,
        conv.person_origin_source_first AS origin_source_first,
        conv.person_is_international_student AS is_international_student,
        conv.person_region AS region,
        conv.person_program_level AS program_level,
        conv.person_program_modality AS program_modality,
        -- Program name: ALWAYS from application table
        app.program_name AS program_name
    FROM `unified-data-platform-prod.udp_url.conversion` AS conv
    LEFT JOIN `unified-data-platform-prod.udp_udl.application` AS app
        ON conv.application_id = app.id
        AND conv.institution_id = app.institution_id,
    UNNEST([
        STRUCT(conv.person_prospect_date AS funnel_day, 'Prospect' AS funnel_stage_for_day),
        STRUCT(conv.person_inquired_date, 'Inquiry'),
        STRUCT(CASE WHEN LOWER(conv.app_type) LIKE '%common%' THEN conv.app_submitted_date ELSE conv.app_created_date END, 'App Created'),
        STRUCT(conv.app_submitted_date, 'App Submitted'),
        STRUCT(conv.app_admitted_date, 'Admitted'),
        STRUCT(conv.app_deposited_date, 'Deposit'),
        STRUCT(conv.app_enrolled_date, 'Enrollment'),
        STRUCT(conv.app_exit_date, 'Exit')
    ]) AS stage
    WHERE stage.funnel_day IS NOT NULL
),

conversion_filtered AS (
    SELECT *
    FROM conversion_unpivoted
    WHERE funnel_day <= CURRENT_DATE()
        AND entry_term_year IN (2024, 2025, 2026)
        AND entry_term_semester = 'Fall'
),

conversion_daily AS (
    SELECT
        institution_id,
        entry_term_year,
        entry_term_semester,
        student_type,
        is_international_student,
        origin_source_first,
        region,
        program_level,
        program_modality,
        program_name,
        funnel_day AS day,
        EXTRACT(YEAR FROM funnel_day) AS event_year,
        EXTRACT(MONTH FROM funnel_day) AS event_month,
        FORMAT_DATE('%b', funnel_day) AS event_month_name,
        -- Funnel counts (same logic as dbt model)
        COUNT(DISTINCT CASE WHEN funnel_stage_for_day = 'Prospect' THEN person_id END) AS funnel_prospect_count,
        COUNT(DISTINCT CASE WHEN funnel_stage_for_day = 'Inquiry' THEN person_id END) AS funnel_inquired_count,
        COUNTIF(funnel_stage_for_day = 'App Created') AS funnel_app_created_count,
        COUNTIF(funnel_stage_for_day = 'App Submitted') AS funnel_app_submitted_count,
        COUNTIF(funnel_stage_for_day = 'Admitted') AS funnel_admitted_count,
        COUNTIF(funnel_stage_for_day = 'Deposit') AS funnel_deposited_count,
        COUNTIF(funnel_stage_for_day = 'Enrollment') AS funnel_enrolled_count,
        COUNTIF(funnel_stage_for_day = 'Exit' AND app_exit_after_deposit) AS funnel_exit_after_deposit_count
    FROM conversion_filtered
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14
)

SELECT
    i.name AS institution_name,
    cm.entry_term_year AS term_year,
    cm.entry_term_semester AS term_semester,
    cm.student_type,
    cm.is_international_student AS is_international,
    cm.origin_source_first,
    cm.region AS student_state,
    cm.program_level,
    cm.program_name,
    cm.day,
    cm.event_year,
    cm.event_month,
    cm.event_month_name,
    SUM(cm.funnel_prospect_count) AS total_prospects,
    SUM(cm.funnel_inquired_count) AS total_inquiries,
    SUM(cm.funnel_app_created_count) AS total_app_starts,
    SUM(cm.funnel_app_submitted_count) AS total_app_submits,
    SUM(cm.funnel_admitted_count) AS total_admits,
    SUM(cm.funnel_deposited_count) AS total_deposits,
    SUM(cm.funnel_deposited_count) - SUM(cm.funnel_exit_after_deposit_count) AS total_net_deposits,
    SUM(cm.funnel_enrolled_count) AS total_enrolled
FROM conversion_daily AS cm
INNER JOIN `unified-data-platform-prod.udp_udl.institution` AS i
    ON cm.institution_id = i.id
WHERE i.name = @institution_name
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
ORDER BY term_year, day
