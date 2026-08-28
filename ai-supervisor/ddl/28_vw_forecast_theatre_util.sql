CREATE VIEW ops.vw_forecast_theatre_util (
  SiteID,
  SiteName,
  ForecastDate,
  UtilForecast,
  UtilLower,
  UtilUpper)
DEFAULT COLLATION UTF8_BINARY
WITH SCHEMA COMPENSATION
AS SELECT f.SiteID, d.SiteName, f.ds AS ForecastDate,
         round(f.y_forecast,1) AS UtilForecast, round(f.y_lower,1) AS UtilLower, round(f.y_upper,1) AS UtilUpper
  FROM ramsay_health.ops.fc_theatre_util f JOIN ramsay_health.ops.dim_site d ON f.SiteID=d.SiteID
;
