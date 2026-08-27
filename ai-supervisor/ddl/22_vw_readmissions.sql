CREATE VIEW ops.vw_readmissions (
  PatientKey,
  ReferralID,
  ServiceName,
  raised,
  prev_raised,
  days_since_prev,
  is_readmission)
DEFAULT COLLATION UTF8_BINARY
WITH SCHEMA COMPENSATION
AS WITH r AS (
  SELECT PatientKey, ReferralID, ServiceName,
         CAST(ReferralRaisedDate AS TIMESTAMP) AS raised,
         LAG(CAST(ReferralRaisedDate AS TIMESTAMP)) OVER (PARTITION BY PatientKey ORDER BY CAST(ReferralRaisedDate AS TIMESTAMP)) AS prev_raised
  FROM ramsay_health.ops.tbreferrals
)
SELECT r.*, DATEDIFF(raised, prev_raised) AS days_since_prev,
       CASE WHEN prev_raised IS NOT NULL AND DATEDIFF(raised, prev_raised) <= 30 THEN 1 ELSE 0 END AS is_readmission
FROM r
;
