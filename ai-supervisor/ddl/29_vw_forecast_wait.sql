CREATE VIEW ops.vw_forecast_wait (
  SiteID,
  SiteName,
  ForecastDate,
  WaitWeeksForecast,
  WaitLower,
  WaitUpper)
DEFAULT COLLATION UTF8_BINARY
WITH SCHEMA COMPENSATION
AS SELECT f.SiteID, d.SiteName, f.ds AS ForecastDate,
         round(f.y_forecast,1) AS WaitWeeksForecast, round(f.y_lower,1) AS WaitLower, round(f.y_upper,1) AS WaitUpper
  FROM ramsay_health.ops.fc_wait f JOIN ramsay_health.ops.dim_site d ON f.SiteID=d.SiteID
;
