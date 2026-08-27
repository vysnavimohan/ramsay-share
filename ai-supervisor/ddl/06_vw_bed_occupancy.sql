CREATE VIEW ops.vw_bed_occupancy (
  BedDate,
  SiteID,
  SiteName,
  BedsAvailable,
  BedsOccupied,
  OccupancyPct,
  Admissions,
  Discharges)
DEFAULT COLLATION UTF8_BINARY
WITH SCHEMA COMPENSATION
AS SELECT b.BedDate::DATE AS BedDate, b.SiteID, d.SiteName, CAST(b.BedsAvailable AS INT) AS BedsAvailable,
       CAST(b.BedsOccupied AS INT) AS BedsOccupied, CAST(b.OccupancyPct AS DOUBLE) AS OccupancyPct,
       CAST(b.Admissions AS INT) AS Admissions, CAST(b.Discharges AS INT) AS Discharges
FROM ramsay_health.ops.fact_bed_day b JOIN ramsay_health.ops.dim_site d ON b.SiteID = d.SiteID
;
