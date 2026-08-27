CREATE VIEW ops.vw_waiting_list (
  ReferralID,
  SiteID,
  SiteName,
  ServiceName,
  PayorType,
  WeeksWaiting,
  CurrentWaitDays,
  WaitBand,
  RTTBreach,
  ActiveFlag,
  Subsection,
  ReferralUrgency,
  TCITS,
  AdmittedTS)
DEFAULT COLLATION UTF8_BINARY
WITH SCHEMA COMPENSATION
AS SELECT w.ReferralID, w.LocationID AS SiteID, w.LocationName AS SiteName, w.ServiceName,
       w.PayorType, CAST(w.WeeksWaiting AS INT) AS WeeksWaiting, CAST(w.CurrentWait AS INT) AS CurrentWaitDays,
       CASE WHEN CAST(w.WeeksWaiting AS INT) <= 18 THEN 'Within 18wk'
            WHEN CAST(w.WeeksWaiting AS INT) <= 26 THEN '18-26wk'
            WHEN CAST(w.WeeksWaiting AS INT) <= 52 THEN '26-52wk' ELSE '52wk+' END AS WaitBand,
       CASE WHEN CAST(w.WeeksWaiting AS INT) > 18 THEN 1 ELSE 0 END AS RTTBreach,
       CAST(w.ActiveFlag AS INT) AS ActiveFlag, w.Subsection, w.ReferralUrgency,
       CAST(w.TCIDate AS TIMESTAMP) AS TCITS, CAST(w.AdmittedDate AS TIMESTAMP) AS AdmittedTS
FROM ramsay_health.ops.tbwlmds w
;
