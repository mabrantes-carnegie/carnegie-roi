-- ============================================================
-- Q8: Digital Performance Overview
-- Source: tinman.v_kpi_campaign
-- Powers: Digital > Overview tab
-- Grain: client × group × subgroup × product × campaign × day
-- Export as: q8_digital_overview.csv
-- ============================================================
SELECT
    client_name,
    campaign_group_name                                     AS group_name,
    campaign_subgroup_name                                  AS subgroup_name,
    product_group_name                                      AS strategy,
    product_name,
    campaign_name,
    day,
    EXTRACT(YEAR FROM day)                                  AS event_year,
    EXTRACT(MONTH FROM day)                                 AS event_month,
    FORMAT_DATE('%b', day)                                  AS event_month_name,
    SUM(impressions)                                        AS impressions,
    SUM(clicks)                                             AS clicks,
    SUM(conversions)                                        AS direct_conversions,
    SUM(view_through_conversions)                           AS view_through_conversions,
    SUM(leads)                                              AS in_platform_leads,
    SUM(conversions) + SUM(view_through_conversions)
        + SUM(leads)                                        AS total_interactions,
    SUM(cost)                                               AS cost,
    SUM(budget)                                             AS budget,
    SUM(followers)                                          AS followers,
    SUM(likes)                                              AS likes,
    SUM(shares)                                             AS shares,
    SUM(comments)                                           AS comments,
    SUM(video_starts)                                       AS video_starts,
    SUM(video_25)                                           AS video_25pct,
    SUM(video_50)                                           AS video_50pct,
    SUM(video_75)                                           AS video_75pct,
    SUM(video_100)                                          AS video_completions
FROM `carnegie-dartlet-1528198422380.tinman.v_kpi_campaign`
WHERE client_name = @client_name
    AND day >= '2024-01-01'
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
ORDER BY day, product_name;


-- ============================================================
-- Q9: Digital Interactions (Key Interactions)
-- Source: tinman.v_kpi_conversion
-- Powers: Digital > Interactions tab
-- Grain: client × group × subgroup × product × campaign × conversion × day
-- Export as: q9_digital_interactions.csv
-- NOTE: interaction_category replicates Looker's Conversion Buckets logic
-- ============================================================
SELECT
    client_name,
    campaign_group_name                                     AS group_name,
    campaign_subgroup_name                                  AS subgroup_name,
    product_name,
    campaign_name,
    conversion                                              AS conversion_name,
    CASE
        WHEN LOWER(conversion) LIKE '%custom_event%'                THEN 'Other'
        WHEN LOWER(conversion) LIKE '%campus tours%'                THEN 'Visit/Event'
        WHEN LOWER(conversion) LIKE '%visit%'                       THEN 'Visit/Event'
        WHEN LOWER(conversion) LIKE '%accept your%'                 THEN 'Enroll/Deposit'
        WHEN LOWER(conversion) LIKE '%confirm admission%'           THEN 'Enroll/Deposit'
        WHEN LOWER(conversion) LIKE '%conversion_purchases%'        THEN 'Enroll/Deposit'
        WHEN LOWER(conversion) LIKE '%admits%'                      THEN 'Enroll/Deposit'
        WHEN LOWER(conversion) LIKE '%enroll%'                      THEN 'Enroll/Deposit'
        WHEN LOWER(conversion) LIKE '%fb_pixel_purchase%'           THEN 'Enroll/Deposit'
        WHEN LOWER(conversion) LIKE '%payment%'                     THEN 'Enroll/Deposit'
        WHEN LOWER(conversion) LIKE '%your admission%'              THEN 'Enroll/Deposit'
        WHEN LOWER(conversion) LIKE '%enroll/deposit%'              THEN 'Enroll/Deposit'
        WHEN LOWER(conversion) LIKE '%admitted%'                    THEN 'Enroll/Deposit'
        WHEN LOWER(conversion) LIKE '%deposit%'                     THEN 'Enroll/Deposit'
        WHEN LOWER(conversion) LIKE '%intent to enroll%'            THEN 'Enroll/Deposit'
        WHEN LOWER(conversion) LIKE '%lead%'                        THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%calls from ads%'              THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%contact%'                     THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%conversion_sign_ups%'         THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%form completion%'             THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%form submission%'             THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%get info%'                    THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%get started%'                 THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%inq.%'                        THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%inquire%'                     THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%inquiry%'                     THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%learn more%'                  THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%onsite_form%'                 THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%request info%'                THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%request more info%'           THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%rfi%'                         THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%send me%'                     THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%fb_pixel_lead%'               THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%thank you page%'              THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%lead form - submit%'          THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%in-platform social lead gen%' THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%get mail%'                    THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%info request%'                THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%form%'                        THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%form fill%'                   THEN 'RFI/Lead Gen'
        WHEN LOWER(conversion) LIKE '%app%'                         THEN 'Apply'
        WHEN LOWER(conversion) LIKE '%application%'                 THEN 'Apply'
        WHEN LOWER(conversion) LIKE '%apply%'                       THEN 'Apply'
        WHEN LOWER(conversion) LIKE '%conversion_subscribe%'        THEN 'Apply'
        WHEN LOWER(conversion) LIKE '%fb_pixel_submit_application%' THEN 'Apply'
        WHEN LOWER(conversion) LIKE '%submit_application_total%'    THEN 'Apply'
        WHEN LOWER(conversion) LIKE '%on_web_subscribe%'            THEN 'Apply'
        WHEN LOWER(conversion) LIKE '%subscribe_website%'           THEN 'Apply'
        WHEN LOWER(conversion) LIKE '%accepted day%'                THEN 'Visit/Event'
        WHEN LOWER(conversion) LIKE '%accepted student%'            THEN 'Visit/Event'
        WHEN LOWER(conversion) LIKE '%advisor%'                     THEN 'Visit/Event'
        WHEN LOWER(conversion) LIKE '%attend%'                      THEN 'Visit/Event'
        WHEN LOWER(conversion) LIKE '%conversion_reserve%'          THEN 'Visit/Event'
        WHEN LOWER(conversion) LIKE '%discovery day%'               THEN 'Visit/Event'
        WHEN LOWER(conversion) LIKE '%event%'                       THEN 'Visit/Event'
        WHEN LOWER(conversion) LIKE '%fb_pixel_complete_registration%' THEN 'Visit/Event'
        WHEN LOWER(conversion) LIKE '%info session%'                THEN 'Visit/Event'
        WHEN LOWER(conversion) LIKE '%information session%'         THEN 'Visit/Event'
        WHEN LOWER(conversion) LIKE '%open house%'                  THEN 'Visit/Event'
        WHEN LOWER(conversion) LIKE '%orientation%'                 THEN 'Visit/Event'
        WHEN LOWER(conversion) LIKE '%preview day%'                 THEN 'Visit/Event'
        WHEN LOWER(conversion) LIKE '%reception%'                   THEN 'Visit/Event'
        WHEN LOWER(conversion) LIKE '%register here%'               THEN 'Visit/Event'
        WHEN LOWER(conversion) LIKE '%rsvp%'                        THEN 'Visit/Event'
        WHEN LOWER(conversion) LIKE '%schedule%'                    THEN 'Visit/Event'
        WHEN LOWER(conversion) LIKE '%tour%'                        THEN 'Visit/Event'
        WHEN REGEXP_CONTAINS(LOWER(conversion), r'unknown')         THEN 'Campus Visit'
        ELSE 'Other'
    END                                                             AS interaction_category,
    day,
    EXTRACT(YEAR FROM day)                                  AS event_year,
    EXTRACT(MONTH FROM day)                                 AS event_month,
    FORMAT_DATE('%b', day)                                  AS event_month_name,
    SUM(conversions)                                        AS direct_conversions,
    SUM(view_through_conversions)                           AS view_through_conversions,
    SUM(leads)                                              AS in_platform_leads,
    SUM(conversions) + SUM(view_through_conversions)
        + SUM(leads)                                        AS total_interactions,
    SUM(cost)                                               AS cost,
    SUM(budget)                                             AS budget
FROM `carnegie-dartlet-1528198422380.tinman.v_kpi_conversion`
WHERE client_name = @client_name
    AND day >= '2024-01-01'
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
ORDER BY day, interaction_category, conversion_name;


-- ============================================================
-- Q10: Digital Geography — Region Level
-- Source: tinman.v_kpi_geo
-- Powers: Digital > Geography tab
-- Grain: client × group × subgroup × product × region × day
-- Export as: q10_digital_geo.csv
-- ============================================================
SELECT
    client_name,
    campaign_group_name                                     AS group_name,
    campaign_subgroup_name                                  AS subgroup_name,
    product_name,
    region,
    day,
    EXTRACT(YEAR FROM day)                                  AS event_year,
    EXTRACT(MONTH FROM day)                                 AS event_month,
    FORMAT_DATE('%b', day)                                  AS event_month_name,
    SUM(impressions)                                        AS impressions,
    SUM(clicks)                                             AS clicks,
    SUM(conversions)                                        AS direct_conversions,
    SUM(view_through_conversions)                           AS view_through_conversions,
    SUM(leads)                                              AS in_platform_leads,
    SUM(conversions) + SUM(view_through_conversions)
        + SUM(leads)                                        AS total_conversions,
    SUM(cost)                                               AS cost,
    SUM(budget)                                             AS budget
FROM `carnegie-dartlet-1528198422380.tinman.v_kpi_geo`
WHERE client_name = @client_name
    AND day >= '2024-01-01'
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9
ORDER BY day, impressions DESC;


-- ============================================================
-- Q11a: Digital Creative (ALL platforms)
-- Sources: tinman.v_kpi_ad_group + tinman.v_kpi_creative
-- Powers: Digital > Creative tab > all creative tables
-- Export as: q11_digital_creative.csv
-- Python filtering logic:
--   Display Creative      → ad_group IS NOT NULL
--   Display by Ad Size    → creative IS NOT NULL AND product_name IN display list
--   Meta/YouTube/etc      → creative IS NOT NULL AND product_name NOT IN display list
-- Validated with client-scoped source data.
-- ============================================================

-- Part 1: Display products at ad_group level (v_kpi_ad_group)
SELECT
    client_name,
    campaign_group_name                                     AS group_name,
    campaign_subgroup_name                                  AS subgroup_name,
    product_name,
    platform_campaign_name,
    campaign_name,
    ad_group,
    CAST(NULL AS STRING)                                    AS creative,
    CAST(NULL AS STRING)                                    AS ad_description,
    image_url,
    ad_url,
    preview_url,
    CAST(NULL AS STRING)                                    AS segment_group,
    day,
    EXTRACT(YEAR FROM day)                                  AS event_year,
    EXTRACT(MONTH FROM day)                                 AS event_month,
    FORMAT_DATE('%b', day)                                  AS event_month_name,
    SUM(impressions)                                        AS impressions,
    SUM(clicks)                                             AS clicks,
    SUM(conversions)                                        AS direct_conversions,
    SUM(view_through_conversions)                           AS view_through_conversions,
    SUM(leads)                                              AS in_platform_leads,
    SUM(conversions) + SUM(view_through_conversions)
        + SUM(leads)                                        AS total_conversions,
    SUM(cost)                                               AS cost,
    SUM(budget)                                             AS budget,
    SUM(followers)                                          AS followers,
    SUM(likes)                                              AS likes,
    SUM(shares)                                             AS shares,
    SUM(comments)                                           AS comments,
    SUM(visits)                                             AS visits,
    SUM(video_starts)                                       AS video_starts,
    SUM(video_100)                                          AS video_completions,
    CAST(NULL AS FLOAT64)                                   AS video_avg
FROM `carnegie-dartlet-1528198422380.tinman.v_kpi_ad_group`
WHERE client_name = @client_name
    AND day >= '2024-01-01'
    AND product_name IN (
        'Display', 'IP Targeting', 'Audience Select',
        'Mobile Footprint', 'Discovery', 'Mobile Location Targeting'
    )
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17

UNION ALL

-- Part 2: All platforms at creative level (v_kpi_creative)
SELECT
    client_name,
    campaign_group_name                                     AS group_name,
    campaign_subgroup_name                                  AS subgroup_name,
    product_name,
    platform_campaign_name,
    campaign_name,
    CAST(NULL AS STRING)                                    AS ad_group,
    creative,
    ad_description,
    image_url,
    ad_url,
    preview_url,
    segment_group,
    day,
    EXTRACT(YEAR FROM day)                                  AS event_year,
    EXTRACT(MONTH FROM day)                                 AS event_month,
    FORMAT_DATE('%b', day)                                  AS event_month_name,
    SUM(impressions)                                        AS impressions,
    SUM(clicks)                                             AS clicks,
    SUM(conversions)                                        AS direct_conversions,
    SUM(view_through_conversions)                           AS view_through_conversions,
    SUM(leads)                                              AS in_platform_leads,
    SUM(conversions) + SUM(view_through_conversions)
        + SUM(leads)                                        AS total_conversions,
    SUM(cost)                                               AS cost,
    SUM(budget)                                             AS budget,
    SUM(followers)                                          AS followers,
    SUM(likes)                                              AS likes,
    SUM(shares)                                             AS shares,
    SUM(comments)                                           AS comments,
    SUM(visits)                                             AS visits,
    SUM(video_starts)                                       AS video_starts,
    SUM(video_100)                                          AS video_completions,
    AVG(video_avg)                                          AS video_avg
FROM `carnegie-dartlet-1528198422380.tinman.v_kpi_creative`
WHERE client_name = @client_name
    AND day >= '2024-01-01'
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17
ORDER BY product_name, day, impressions DESC;


-- ============================================================
-- Q11b: PPC Keyword Performance
-- Source: tinman.v_kpi_keyword
-- Powers: Digital > Creative tab > PPC keyword table
-- Grain: client × campaign × keyword × match_type × day
-- Export as: q11_digital_keywords.csv
-- ============================================================
SELECT
    client_name,
    platform_campaign_name,
    campaign_name,
    product_name,
    keyword,
    match_type,
    day,
    EXTRACT(YEAR FROM day)                                  AS event_year,
    EXTRACT(MONTH FROM day)                                 AS event_month,
    FORMAT_DATE('%b', day)                                  AS event_month_name,
    SUM(impressions)                                        AS impressions,
    SUM(clicks)                                             AS clicks,
    SUM(conversions)                                        AS direct_conversions,
    SUM(cost)                                               AS cost,
    SUM(budget)                                             AS budget
FROM `carnegie-dartlet-1528198422380.tinman.v_kpi_keyword`
WHERE client_name = @client_name
    AND day >= '2024-01-01'
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
ORDER BY day, impressions DESC;


-- ============================================================
-- Q11c: YouTube Creative (daily grain for correct video_avg)
-- Source: tinman.v_kpi_creative
-- Powers: Digital > Creative tab > YouTube Creative table
-- Grain: client × campaign × creative × day (NO monthly aggregation)
-- NOTE: video_avg must NOT be aggregated monthly — AVG(video_avg)
--       over daily rows = 3.55% ✅ (matches Looker)
--       AVG over monthly pre-aggregated rows = 2.38% ❌ (wrong)
-- Export as: q11_youtube_creative.csv
-- Python: video_avg = df_youtube.groupby([...])['video_avg'].mean()
-- Validated: AVG(video_avg) Jul 25–Mar 26 = 3.55% ✅
-- ============================================================
SELECT
    client_name,
    campaign_group_name                                     AS group_name,
    campaign_subgroup_name                                  AS subgroup_name,
    product_name,
    platform_campaign_name,
    campaign_name,
    creative,
    ad_description,
    image_url,
    ad_url,
    preview_url,
    segment_group                                           AS ad_group,
    day,
    SUM(impressions)                                        AS impressions,
    SUM(clicks)                                             AS clicks,
    SUM(conversions)                                        AS direct_conversions,
    SUM(view_through_conversions)                           AS view_through_conversions,
    SUM(leads)                                              AS in_platform_leads,
    SUM(conversions) + SUM(view_through_conversions)
        + SUM(leads)                                        AS total_conversions,
    SUM(cost)                                               AS cost,
    SUM(budget)                                             AS budget,
    SUM(video_starts)                                       AS video_starts,
    SUM(video_100)                                          AS video_completions,
    AVG(video_avg)                                          AS video_avg
FROM `carnegie-dartlet-1528198422380.tinman.v_kpi_creative`
WHERE client_name = @client_name
    AND day >= '2024-01-01'
    AND product_name IN ('YouTube', 'Youtube')
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
ORDER BY day, impressions DESC;


-- ============================================================
-- Q12: Optimization Notes & Performance Insights
-- Source: tinman.v_opnote
-- Powers: Digital > Insights tab
-- Grain: one row per note (deduplicate in Python by day+note_type+notes)
-- NOTE: is_internal = '1' for internal notes. Filter != '1' for external only.
-- Export as: q12_digital_notes.csv
-- ============================================================
SELECT DISTINCT
    client_name,
    campaign_group_name                                     AS group_name,
    campaign_subgroup_name                                  AS subgroup_name,
    product_name,
    product_group_name                                      AS strategy,
    campaign_name,
    day,
    type                                                    AS note_type,
    is_milestone,
    notes,
    created_by
FROM `carnegie-dartlet-1528198422380.tinman.v_opnote`
WHERE client_name = @client_name
    AND day >= '2024-01-01'
    AND is_internal != '1'
ORDER BY day DESC;
