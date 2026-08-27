CREATE VIEW ops.vw_referral_flow (
  ReferralID,
  PatientKey,
  ServiceName,
  PayorType,
  ReferralUrgency,
  AgeAtDateOfReferral,
  ReferralRaisedTS,
  ReferralReceivedTS,
  FirstApptTS,
  HasAdmission,
  HasVisit,
  SiteID,
  SiteName,
  WeeksWaiting,
  CurrentWaitDays,
  RTTStatusID,
  ClockStopFlag,
  Subsection)
DEFAULT COLLATION UTF8_BINARY
WITH SCHEMA COMPENSATION
AS SELECT r.ReferralID, r.PatientKey, r.ServiceName, r.PayorType, r.ReferralUrgency,
       r.AgeAtDateOfReferral, CAST(r.ReferralRaisedDate AS TIMESTAMP) AS ReferralRaisedTS,
       CAST(r.ReferralReceivedDate AS TIMESTAMP) AS ReferralReceivedTS,
       CAST(r.FirstApptDate AS TIMESTAMP) AS FirstApptTS, r.HasAdmission, r.HasVisit,
       w.LocationID AS SiteID, w.LocationName AS SiteName, CAST(w.WeeksWaiting AS INT) AS WeeksWaiting,
       CAST(w.CurrentWait AS INT) AS CurrentWaitDays, w.RTTStatusID, w.ClockStopFlag, w.Subsection
FROM ramsay_health.ops.tbreferrals r
LEFT JOIN ramsay_health.ops.tbwlmds w ON r.ReferralID = w.ReferralID
;
