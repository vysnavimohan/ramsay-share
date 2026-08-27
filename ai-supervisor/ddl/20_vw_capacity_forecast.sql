CREATE VIEW ops.vw_capacity_forecast (
  SiteID,
  SiteName,
  ForecastDate,
  AdmissionsForecast,
  ForecastLower,
  ForecastUpper)
DEFAULT COLLATION UTF8_BINARY
WITH SCHEMA COMPENSATION
AS SELECT f.SiteID, d.SiteName, f.ds AS ForecastDate, round(f.y_forecast,1) AS AdmissionsForecast,
         round(f.y_lower,1) AS ForecastLower, round(f.y_upper,1) AS ForecastUpper
  FROM ramsay_health.ops.fc_admissions f JOIN ramsay_health.ops.dim_site d ON f.SiteID=d.SiteID
;
