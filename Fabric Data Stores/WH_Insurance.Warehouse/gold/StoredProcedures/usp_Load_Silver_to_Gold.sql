CREATE PROCEDURE gold.usp_Load_Silver_to_Gold
AS
/* ================================================================
   Silver → Gold KPI Load Script (All 6 Gold tables)
   Warehouse: WH_Insurance
   Target  : gold.<tables>
   Source  : LH_Insurance.Silver.<tables>  (Lakehouse SQL analytics endpoint)
   ================================================================ */

DECLARE @Lakehouse    sysname = N'LH_Insurance';
DECLARE @SilverSchema sysname = N'Silver';

DECLARE @sql nvarchar(max);

-- =================================================================
-- 1) gold.gold_claims_by_adjuster
-- =================================================================
SET @sql = N'
DELETE FROM gold.gold_claims_by_adjuster;

INSERT INTO gold.gold_claims_by_adjuster
(
  adjuster_id,
  adjuster_full_name,
  home_office_id,
  total_claims_assigned,
  open_claims,
  closed_claims,
  pending_claims,
  avg_estimated_loss,
  total_approved_amount,
  avg_approved_amount,
  approval_rate_pct,
  high_priority_claims,
  avg_days_to_file,
  _gold_processed_ts
)
SELECT
  c.adjuster_id,
  CONCAT(a.first_name, '' '', a.last_name) AS adjuster_full_name,
  a.home_office_id,
  COUNT(*) AS total_claims_assigned,
  SUM(CASE WHEN c.status = ''Active''  THEN 1 ELSE 0 END) AS open_claims,
  SUM(CASE WHEN c.status = ''Closed''  THEN 1 ELSE 0 END) AS closed_claims,
  SUM(CASE WHEN c.status = ''Pending'' THEN 1 ELSE 0 END) AS pending_claims,
  CAST(AVG(CAST(c.estimated_loss  AS decimal(18,2))) AS decimal(18,2)) AS avg_estimated_loss,
  CAST(SUM(CAST(c.approved_amount AS decimal(18,2))) AS decimal(18,2)) AS total_approved_amount,
  CAST(AVG(CAST(c.approved_amount AS decimal(18,2))) AS decimal(18,2)) AS avg_approved_amount,
  CAST(
    CASE WHEN SUM(CAST(c.estimated_loss AS float)) = 0 THEN NULL
         ELSE (SUM(CAST(c.approved_amount AS float)) / SUM(CAST(c.estimated_loss AS float))) * 100
    END
    AS decimal(8,2)
  ) AS approval_rate_pct,
  SUM(CASE WHEN c.priority = ''High'' THEN 1 ELSE 0 END) AS high_priority_claims,
  CAST(AVG(CAST(ABS(DATEDIFF(day, c.incident_date, c.filed_date)) AS float)) AS decimal(8,1)) AS avg_days_to_file,
  CAST(SYSDATETIME() AS datetime2(6)) AS _gold_processed_ts
FROM ' + QUOTENAME(@Lakehouse) + N'.' + QUOTENAME(@SilverSchema) + N'.claims c
LEFT JOIN ' + QUOTENAME(@Lakehouse) + N'.' + QUOTENAME(@SilverSchema) + N'.adjusters a
  ON a.adjuster_id = c.adjuster_id
GROUP BY
  c.adjuster_id,
  CONCAT(a.first_name, '' '', a.last_name),
  a.home_office_id;
';
EXEC sp_executesql @sql;

-- =================================================================
-- 2) gold.gold_avg_loss_by_claim_type
-- =================================================================




SET @sql = N'DELETE FROM gold.gold_avg_loss_by_claim_type;

WITH StatusCounts AS (
  SELECT
    claim_type,
    status,
    COUNT(*) AS status_count,
    ROW_NUMBER() OVER (PARTITION BY claim_type ORDER BY COUNT(*) DESC) AS rn
  FROM ' + QUOTENAME(@Lakehouse) + N'.' + QUOTENAME(@SilverSchema) + N'.claims
  GROUP BY claim_type, status
),
ModeStatus AS (
  SELECT claim_type, status AS most_common_status
  FROM StatusCounts
  WHERE rn = 1
)
INSERT INTO gold.gold_avg_loss_by_claim_type
(
  claim_type,
  total_claims,
  avg_estimated_loss,
  max_estimated_loss,
  min_estimated_loss,
  avg_approved_amount,
  total_approved_amount,
  avg_approval_rate_pct,
  most_common_status,
  avg_days_to_file,
  _gold_processed_ts
)
SELECT
  c.claim_type,
  COUNT(*) AS total_claims,
  CAST(AVG(CAST(c.estimated_loss AS decimal(18,2))) AS decimal(18,2)) AS avg_estimated_loss,
  CAST(MAX(CAST(c.estimated_loss AS decimal(18,2))) AS decimal(18,2)) AS max_estimated_loss,
  CAST(MIN(CAST(c.estimated_loss AS decimal(18,2))) AS decimal(18,2)) AS min_estimated_loss,
  CAST(AVG(CAST(c.approved_amount AS decimal(18,2))) AS decimal(18,2)) AS avg_approved_amount,
  CAST(SUM(CAST(c.approved_amount AS decimal(18,2))) AS decimal(18,2)) AS total_approved_amount,
  CAST(
    CASE WHEN SUM(CAST(c.estimated_loss AS float)) = 0 THEN NULL
         ELSE (SUM(CAST(c.approved_amount AS float)) / SUM(CAST(c.estimated_loss AS float))) * 100
    END
    AS decimal(8,2)
  ) AS avg_approval_rate_pct,
  ms.most_common_status,
  CAST(AVG(CAST(ABS(DATEDIFF(day, c.incident_date, c.filed_date)) AS float)) AS decimal(8,1)) AS avg_days_to_file,
  CAST(SYSDATETIME() AS datetime2(6)) AS _gold_processed_ts
FROM ' + QUOTENAME(@Lakehouse) + N'.' + QUOTENAME(@SilverSchema) + N'.claims c
LEFT JOIN ModeStatus ms
  ON ms.claim_type = c.claim_type
GROUP BY c.claim_type, ms.most_common_status;
';
EXEC sp_executesql @sql;

-- =================================================================
-- 3) gold.gold_fraud_flags
-- =================================================================



SET @sql = N'DELETE FROM gold.gold_fraud_flags;

WITH AssetClaimCounts AS (
  SELECT asset_id, COUNT(*) AS asset_claim_count
  FROM ' + QUOTENAME(@Lakehouse) + N'.' + QUOTENAME(@SilverSchema) + N'.claims
  GROUP BY asset_id
),
PolicyholderClaimCounts AS (
  SELECT policyholder_id, COUNT(*) AS ph_claim_count
  FROM ' + QUOTENAME(@Lakehouse) + N'.' + QUOTENAME(@SilverSchema) + N'.claims
  GROUP BY policyholder_id
),
AdjusterActiveCounts AS (
  SELECT adjuster_id, COUNT(*) AS adj_active_count
  FROM ' + QUOTENAME(@Lakehouse) + N'.' + QUOTENAME(@SilverSchema) + N'.claims
  WHERE status = ''Active''
  GROUP BY adjuster_id
),
Base AS (
  SELECT
    c.claim_id,
    c.claim_number,
    c.policyholder_id,
    c.adjuster_id,
    c.asset_id,
    c.policy_id,
    c.estimated_loss,
    c.approved_amount,
    c.incident_date,
    c.filed_date,
    p.coverage_amount,
    p.effective_date,
    a.max_active_claims,
    ac.asset_claim_count,
    pc.ph_claim_count,
    aa.adj_active_count
  FROM ' + QUOTENAME(@Lakehouse) + N'.' + QUOTENAME(@SilverSchema) + N'.claims c
  LEFT JOIN ' + QUOTENAME(@Lakehouse) + N'.' + QUOTENAME(@SilverSchema) + N'.policies p
    ON p.policy_id = c.policy_id
  LEFT JOIN ' + QUOTENAME(@Lakehouse) + N'.' + QUOTENAME(@SilverSchema) + N'.adjusters a
    ON a.adjuster_id = c.adjuster_id
  LEFT JOIN AssetClaimCounts ac
    ON ac.asset_id = c.asset_id
  LEFT JOIN PolicyholderClaimCounts pc
    ON pc.policyholder_id = c.policyholder_id
  LEFT JOIN AdjusterActiveCounts aa
    ON aa.adjuster_id = c.adjuster_id
),
Flags AS (
  SELECT
    claim_id, claim_number, policyholder_id, adjuster_id, asset_id, policy_id,

    CAST(CASE WHEN estimated_loss > (coverage_amount * 0.80) THEN 1 ELSE 0 END AS bit) AS flag_high_loss_vs_coverage,
    CAST(CASE WHEN filed_date < incident_date THEN 1 ELSE 0 END AS bit) AS flag_filed_before_incident,
    CAST(CASE WHEN asset_claim_count > 2 THEN 1 ELSE 0 END AS bit) AS flag_multiple_claims_same_asset,
    CAST(CASE WHEN approved_amount IS NOT NULL AND estimated_loss IS NOT NULL
                   AND approved_amount < (estimated_loss * 0.20)
              THEN 1 ELSE 0 END AS bit) AS flag_low_approval_ratio,
    CAST(CASE WHEN adj_active_count > (max_active_claims * 0.80) THEN 1 ELSE 0 END AS bit) AS flag_adjuster_high_volume,
    CAST(CASE WHEN DATEDIFF(day, effective_date, filed_date) < 90 THEN 1 ELSE 0 END AS bit) AS flag_new_policy_claim,
    CAST(CASE WHEN ph_claim_count > 3 THEN 1 ELSE 0 END AS bit) AS flag_repeat_policyholder
  FROM Base
),
Scored AS (
  SELECT
    *,
    (CASE WHEN flag_high_loss_vs_coverage = 1 THEN 20 ELSE 0 END) +
    (CASE WHEN flag_filed_before_incident = 1 THEN 25 ELSE 0 END) +
    (CASE WHEN flag_multiple_claims_same_asset = 1 THEN 15 ELSE 0 END) +
    (CASE WHEN flag_low_approval_ratio = 1 THEN 10 ELSE 0 END) +
    (CASE WHEN flag_adjuster_high_volume = 1 THEN 10 ELSE 0 END) +
    (CASE WHEN flag_new_policy_claim = 1 THEN 10 ELSE 0 END) +
    (CASE WHEN flag_repeat_policyholder = 1 THEN 10 ELSE 0 END) AS fraud_score
  FROM Flags
)
INSERT INTO gold.gold_fraud_flags
(
  claim_id, claim_number, policyholder_id, adjuster_id, asset_id, policy_id,
  fraud_score, fraud_risk_label,
  flag_high_loss_vs_coverage,
  flag_filed_before_incident,
  flag_multiple_claims_same_asset,
  flag_low_approval_ratio,
  flag_adjuster_high_volume,
  flag_new_policy_claim,
  flag_repeat_policyholder,
  _gold_processed_ts
)
SELECT
  claim_id, claim_number, policyholder_id, adjuster_id, asset_id, policy_id,
  fraud_score,
  CASE WHEN fraud_score >= 75 THEN ''Critical''
       WHEN fraud_score >= 50 THEN ''High''
       WHEN fraud_score >= 25 THEN ''Medium''
       ELSE ''Low'' END AS fraud_risk_label,
  flag_high_loss_vs_coverage,
  flag_filed_before_incident,
  flag_multiple_claims_same_asset,
  flag_low_approval_ratio,
  flag_adjuster_high_volume,
  flag_new_policy_claim,
  flag_repeat_policyholder,
  CAST(SYSDATETIME() AS datetime2(6)) AS _gold_processed_ts
FROM Scored;
';
EXEC sp_executesql @sql;

-- =================================================================
-- 4) gold.gold_claims_summary_by_office
-- =================================================================



SET @sql = N'
DELETE FROM gold.gold_claims_summary_by_office;

WITH FraudHi AS (
  SELECT claim_id,
         CASE WHEN fraud_score >= 50 THEN 1 ELSE 0 END AS is_fraud_flagged
  FROM gold.gold_fraud_flags
),
TopType AS (
  SELECT
    c.office_id,
    c.claim_type,
    COUNT(*) AS type_count,
    ROW_NUMBER() OVER (PARTITION BY c.office_id ORDER BY COUNT(*) DESC) AS rn
  FROM ' + QUOTENAME(@Lakehouse) + N'.' + QUOTENAME(@SilverSchema) + N'.claims c
  GROUP BY c.office_id, c.claim_type
),
TopClaimType AS (
  SELECT office_id, claim_type AS top_claim_type
  FROM TopType
  WHERE rn = 1
)
INSERT INTO gold.gold_claims_summary_by_office
(
  office_id, office_name, city, state,
  total_claims, open_claims, closed_claims,
  total_estimated_loss, total_approved_amount, avg_loss_per_claim,
  fraud_flag_count, top_claim_type,
  _gold_processed_ts
)
SELECT
  c.office_id,
  o.name AS office_name,
  o.city,
  o.state,
  COUNT(*) AS total_claims,
  SUM(CASE WHEN c.status = ''Active'' THEN 1 ELSE 0 END) AS open_claims,
  SUM(CASE WHEN c.status = ''Closed'' THEN 1 ELSE 0 END) AS closed_claims,
  CAST(SUM(CAST(c.estimated_loss AS decimal(18,2))) AS decimal(18,2)) AS total_estimated_loss,
  CAST(SUM(CAST(c.approved_amount AS decimal(18,2))) AS decimal(18,2)) AS total_approved_amount,
  CAST(AVG(CAST(c.estimated_loss AS decimal(18,2))) AS decimal(18,2)) AS avg_loss_per_claim,
  SUM(COALESCE(f.is_fraud_flagged, 0)) AS fraud_flag_count,
  t.top_claim_type,
  CAST(SYSDATETIME() AS datetime2(6)) AS _gold_processed_ts
FROM ' + QUOTENAME(@Lakehouse) + N'.' + QUOTENAME(@SilverSchema) + N'.claims c
LEFT JOIN ' + QUOTENAME(@Lakehouse) + N'.' + QUOTENAME(@SilverSchema) + N'.offices o
  ON o.office_id = c.office_id
LEFT JOIN FraudHi f
  ON f.claim_id = c.claim_id
LEFT JOIN TopClaimType t
  ON t.office_id = c.office_id
GROUP BY
  c.office_id, o.name, o.city, o.state, t.top_claim_type;
';
EXEC sp_executesql @sql;

-- =================================================================
-- 5) gold.gold_policyholder_risk_profile
-- =================================================================


SET @sql = N'
DELETE FROM gold.gold_policyholder_risk_profile;

WITH PolicyCounts AS (
  SELECT policyholder_id, COUNT(*) AS total_policies
  FROM ' + QUOTENAME(@Lakehouse) + N'.' + QUOTENAME(@SilverSchema) + N'.policies
  GROUP BY policyholder_id
),
ClaimAgg AS (
  SELECT
    policyholder_id,
    COUNT(*) AS total_claims,
    SUM(CAST(estimated_loss AS decimal(18,2)))  AS total_estimated_loss,
    SUM(CAST(approved_amount AS decimal(18,2))) AS total_approved_amount,
    AVG(CAST(estimated_loss AS decimal(18,2)))  AS avg_claim_amount
  FROM ' + QUOTENAME(@Lakehouse) + N'.' + QUOTENAME(@SilverSchema) + N'.claims
  GROUP BY policyholder_id
)
INSERT INTO gold.gold_policyholder_risk_profile
(
  policyholder_id, full_name, policyholder_type, risk_score,
  total_policies, total_claims,
  total_estimated_loss, total_approved_amount, avg_claim_amount,
  claim_frequency_label, combined_risk_label,
  _gold_processed_ts
)
SELECT
  p.policyholder_id,
  p.full_name,
  p.policyholder_type,
  p.risk_score,
  COALESCE(pc.total_policies, 0) AS total_policies,
  COALESCE(ca.total_claims, 0) AS total_claims,
  CAST(COALESCE(ca.total_estimated_loss, 0) AS decimal(18,2))  AS total_estimated_loss,
  CAST(COALESCE(ca.total_approved_amount, 0) AS decimal(18,2)) AS total_approved_amount,
  CAST(COALESCE(ca.avg_claim_amount, 0) AS decimal(18,2))      AS avg_claim_amount,
  CASE WHEN COALESCE(ca.total_claims, 0) >= 5 THEN ''High''
       WHEN COALESCE(ca.total_claims, 0) >= 2 THEN ''Medium''
       ELSE ''Low'' END AS claim_frequency_label,
  CASE
       WHEN p.risk_score >= 700 AND COALESCE(ca.total_claims,0) >= 5 THEN ''Critical''
       WHEN p.risk_score >= 600 OR  COALESCE(ca.total_claims,0) >= 5 THEN ''High''
       WHEN p.risk_score >= 450 OR  COALESCE(ca.total_claims,0) >= 2 THEN ''Medium''
       ELSE ''Low''
  END AS combined_risk_label,
  CAST(SYSDATETIME() AS datetime2(6)) AS _gold_processed_ts
FROM ' + QUOTENAME(@Lakehouse) + N'.' + QUOTENAME(@SilverSchema) + N'.policyholders p
LEFT JOIN PolicyCounts pc
  ON pc.policyholder_id = p.policyholder_id
LEFT JOIN ClaimAgg ca
  ON ca.policyholder_id = p.policyholder_id;
';
EXEC sp_executesql @sql;

-- =================================================================
-- 6) gold.gold_adjuster_performance
-- =================================================================



SET @sql = N'
DELETE FROM gold.gold_adjuster_performance;

WITH ClaimAgg AS (
  SELECT adjuster_id, COUNT(*) AS total_claims_handled
  FROM ' + QUOTENAME(@Lakehouse) + N'.' + QUOTENAME(@SilverSchema) + N'.claims
  GROUP BY adjuster_id
),
EventAgg AS (
  SELECT
    adjuster_id,
    COUNT(*) AS total_claim_events,
    AVG(CAST(cost_usd AS decimal(18,2))) AS avg_cost_per_event,
    AVG(CAST(ABS(DATEDIFF(day, created_at, completed_at)) AS float)) AS avg_days_event_completion
  FROM ' + QUOTENAME(@Lakehouse) + N'.' + QUOTENAME(@SilverSchema) + N'.claim_events
  GROUP BY adjuster_id
),
FraudAgg AS (
  SELECT adjuster_id, COUNT(*) AS high_fraud_claims
  FROM gold.gold_fraud_flags
  WHERE fraud_score >= 50
  GROUP BY adjuster_id
)
INSERT INTO gold.gold_adjuster_performance
(
  adjuster_id, full_name, license_state, specializations, status,
  max_active_claims,
  total_claims_handled, total_claim_events,
  avg_cost_per_event, avg_days_event_completion,
  utilization_rate_pct, high_fraud_claims,
  _gold_processed_ts
)
SELECT
  a.adjuster_id,
  CONCAT(a.first_name, '' '', a.last_name) AS full_name,
  a.license_state,
  a.specializations,
  a.status,
  a.max_active_claims,
  COALESCE(ca.total_claims_handled, 0) AS total_claims_handled,
  COALESCE(ea.total_claim_events, 0)   AS total_claim_events,
  CAST(COALESCE(ea.avg_cost_per_event, 0) AS decimal(18,2)) AS avg_cost_per_event,
  CAST(COALESCE(ea.avg_days_event_completion, 0) AS decimal(8,1)) AS avg_days_event_completion,
  CAST(
    CASE WHEN a.max_active_claims = 0 THEN NULL
         ELSE (CAST(COALESCE(ca.total_claims_handled,0) AS float) / CAST(a.max_active_claims AS float)) * 100
    END
    AS decimal(8,2)
  ) AS utilization_rate_pct,
  COALESCE(fa.high_fraud_claims, 0) AS high_fraud_claims,
  CAST(SYSDATETIME() AS datetime2(6)) AS _gold_processed_ts
FROM ' + QUOTENAME(@Lakehouse) + N'.' + QUOTENAME(@SilverSchema) + N'.adjusters a
LEFT JOIN ClaimAgg ca
  ON ca.adjuster_id = a.adjuster_id
LEFT JOIN EventAgg ea
  ON ea.adjuster_id = a.adjuster_id
LEFT JOIN FraudAgg fa
  ON fa.adjuster_id = a.adjuster_id;
';
EXEC sp_executesql @sql;

PRINT '✅ Completed load for all 6 gold tables from LH_Insurance.Silver.* into WH_Insurance.gold.*';