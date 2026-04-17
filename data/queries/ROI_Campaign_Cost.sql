-- ============================================================
-- QUERY 2: Campaign Lead Source + Cost
--      filtered by campaign_month per academic year definition:
--      Fall N = July (N-1) to June N
-- Export as: q2_campaign_cost.csv
-- ============================================================
WITH
campaign_costs AS (
    SELECT
        cr.campaign_id,
        DATE(cr.campaign_month) AS day,
        CASE
            WHEN cr.campaign_month BETWEEN '2024-07-01' AND '2025-06-30' THEN 2025
            WHEN cr.campaign_month BETWEEN '2025-07-01' AND '2026-06-30' THEN 2026
        END AS term_year,
        SUM(cr.revenue) AS campaign_spend
    FROM `unified-data-platform-prod.udp_udl.campaign_revenue` AS cr
    WHERE cr.campaign_id IN (
        SELECT DISTINCT campaign_id
        FROM `unified-data-platform-prod.udp_url.conversion_campaign_attribution`
        WHERE institution_name = 'Central Washington University'
            AND entry_term_year IN (2024,2025, 2026)
            AND entry_term_semester = 'Fall'
    )
    AND cr.campaign_month BETWEEN '2024-07-01' AND '2026-06-30'
    GROUP BY 1, 2, 3
),
campaign_meta AS (
    SELECT
        c.id           AS campaign_id,
        c.product_group AS campaign_product_group,
        c.service       AS campaign_service,
        c.product       AS campaign_product,
        c.funnel_target AS campaign_funnel_target,
        c.attributable  AS campaign_attributable
    FROM `unified-data-platform-prod.udp_udl.campaign` AS c
),
funnel_by_campaign AS (
    SELECT
        cca.institution_name,
        cca.entry_term_year,
        cca.entry_term_semester,
        cca.campaign_id,
        cca.campaign_funnel_target,
        cca.campaign_attributable,
        DATE(stage.stage_day) AS day,
        COUNT(DISTINCT CASE
            WHEN stage.stage_name = 'Inquiry'
            THEN c.person_id END)                                   AS total_inquiries,
        COUNT(DISTINCT CASE
            WHEN stage.stage_name = 'App Start'
            THEN c.application_id END)                              AS total_app_starts,
        COUNT(DISTINCT CASE
            WHEN stage.stage_name = 'App Submit'
            THEN c.application_id END)                              AS total_app_submits,
        COUNT(DISTINCT CASE
            WHEN stage.stage_name = 'Admit'
            THEN c.application_id END)                              AS total_admits,
        COUNT(DISTINCT CASE
            WHEN stage.stage_name = 'Deposit'
            THEN c.person_id END)                                   AS total_deposits,
        COUNT(DISTINCT CASE
            WHEN stage.stage_name = 'Deposit'
            THEN c.person_id END)
        -
        COUNT(DISTINCT CASE
            WHEN stage.stage_name = 'Exit After Deposit'
            AND  c.app_exit_after_deposit = TRUE
            THEN c.person_id END)                                   AS total_net_deposits,
        COUNT(DISTINCT CASE
            WHEN stage.stage_name = 'Enrolled'
            THEN c.person_id END)                                   AS total_enrolled
    FROM `unified-data-platform-prod.udp_url.conversion_campaign_attribution` AS cca
    INNER JOIN `unified-data-platform-prod.udp_url.conversion` AS c
        ON  cca.person_id      = c.person_id
        AND cca.institution_id = c.institution_id
    INNER JOIN `unified-data-platform-prod.udp_udl.institution` AS i
        ON i.id = cca.institution_id
    CROSS JOIN UNNEST([
        STRUCT(c.person_inquired_date AS stage_day, 'Inquiry' AS stage_name),
        STRUCT(
            CASE
                WHEN LOWER(c.app_type) LIKE '%common%' THEN c.app_submitted_date
                ELSE c.app_created_date
            END AS stage_day,
            'App Start' AS stage_name
        ),
        STRUCT(c.app_submitted_date AS stage_day, 'App Submit' AS stage_name),
        STRUCT(c.app_admitted_date AS stage_day, 'Admit' AS stage_name),
        STRUCT(c.app_deposited_date AS stage_day, 'Deposit' AS stage_name),
        STRUCT(c.app_enrolled_date AS stage_day, 'Enrolled' AS stage_name),
        STRUCT(c.app_exit_date AS stage_day, 'Exit After Deposit' AS stage_name)
    ]) AS stage
    WHERE i.name                              = 'Central Washington University'
        AND cca.entry_term_year               IN (2024,2025, 2026)
        AND cca.entry_term_semester           = 'Fall'
        AND c.person_is_international_student = FALSE
        AND stage.stage_day IS NOT NULL
    GROUP BY 1, 2, 3, 4, 5, 6, 7
),
all_keys AS (
    SELECT campaign_id, term_year, day
    FROM campaign_costs

    UNION DISTINCT

    SELECT campaign_id, entry_term_year AS term_year, day
    FROM funnel_by_campaign
)
SELECT
    COALESCE(f.institution_name, 'Central Washington University') AS institution_name,
    k.term_year                                                    AS term_year,
    COALESCE(f.entry_term_semester, 'Fall')                        AS term_semester,
    cm.campaign_product_group                                      AS lead_source,
    cm.campaign_service,
    COALESCE(f.campaign_funnel_target, cm.campaign_funnel_target)  AS campaign_funnel_target,
    COALESCE(f.campaign_attributable, cm.campaign_attributable)    AS campaign_attributable,
    k.day                                                          AS day,
    EXTRACT(YEAR FROM k.day)                                       AS event_year,
    EXTRACT(MONTH FROM k.day)                                      AS event_month,
    FORMAT_DATE('%b', k.day)                                       AS event_month_name,
    COALESCE(cc.campaign_spend, 0)                                 AS total_cost,
    COALESCE(f.total_inquiries, 0)                                 AS total_inquiries,
    COALESCE(f.total_app_starts, 0)                                AS total_app_starts,
    COALESCE(f.total_app_submits, 0)                               AS total_app_submits,
    COALESCE(f.total_admits, 0)                                    AS total_admits,
    COALESCE(f.total_deposits, 0)                                  AS total_deposits,
    COALESCE(f.total_net_deposits, 0)                              AS total_net_deposits,
    COALESCE(f.total_enrolled, 0)                                  AS total_enrolled
FROM all_keys AS k
LEFT JOIN campaign_costs AS cc
    ON  cc.campaign_id      = k.campaign_id
    AND cc.term_year        = k.term_year
    AND cc.day              = k.day
LEFT JOIN funnel_by_campaign AS f
    ON  f.campaign_id        = k.campaign_id
    AND f.entry_term_year    = k.term_year
    AND f.day               = k.day
INNER JOIN campaign_meta AS cm
    ON cm.campaign_id = k.campaign_id
ORDER BY day, total_cost DESC, lead_source
