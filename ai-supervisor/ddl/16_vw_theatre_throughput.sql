CREATE VIEW ops.vw_theatre_throughput (
  SessionDate,
  SiteID,
  SiteName,
  TheatreID,
  Specialty,
  SessionSlot,
  PlannedMinutes,
  UsedMinutes,
  UtilisationPct,
  CasesScheduled,
  CasesCompleted,
  OnDayCancellations)
DEFAULT COLLATION UTF8_BINARY
WITH SCHEMA COMPENSATION
AS SELECT s.SessionDate::DATE AS SessionDate, s.SiteID, d.SiteName, s.TheatreID, s.Specialty, s.SessionSlot,
       CAST(s.PlannedMinutes AS INT) AS PlannedMinutes, CAST(s.UsedMinutes AS INT) AS UsedMinutes,
       CAST(s.UtilisationPct AS DOUBLE) AS UtilisationPct, CAST(s.CasesScheduled AS INT) AS CasesScheduled,
       CAST(s.CasesCompleted AS INT) AS CasesCompleted, CAST(s.OnDayCancellations AS INT) AS OnDayCancellations
FROM ramsay_health.ops.fact_theatre_session s JOIN ramsay_health.ops.dim_site d ON s.SiteID = d.SiteID
;
