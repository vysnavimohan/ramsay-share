CREATE VIEW ops.vw_diagnostic_capacity (
  SlotDate,
  SiteID,
  SiteName,
  Modality,
  Rooms,
  SlotsCapacity,
  SlotsBooked,
  SlotsAvailable,
  UtilisationPct,
  DNACount)
DEFAULT COLLATION UTF8_BINARY
WITH SCHEMA COMPENSATION
AS SELECT g.SlotDate::DATE AS SlotDate, g.SiteID, d.SiteName, g.Modality, CAST(g.Rooms AS INT) AS Rooms,
       CAST(g.SlotsCapacity AS INT) AS SlotsCapacity, CAST(g.SlotsBooked AS INT) AS SlotsBooked,
       CAST(g.SlotsAvailable AS INT) AS SlotsAvailable, CAST(g.UtilisationPct AS DOUBLE) AS UtilisationPct,
       CAST(g.DNACount AS INT) AS DNACount
FROM ramsay_health.ops.fact_diagnostic_slot g JOIN ramsay_health.ops.dim_site d ON g.SiteID = d.SiteID
;
