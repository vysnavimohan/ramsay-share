CREATE OR REPLACE FUNCTION ramsay_workforce.allocate.fn_find_replacements(gap_id BIGINT)
RETURNS TABLE(
  StaffNumber STRING,
  Name STRING,
  Grade STRING,
  EmployeeType STRING,
  HomeSite STRING,
  distance_km DOUBLE,
  hours_last_7d DOUBLE,
  contract_rank INT,
  wtd_ok BOOLEAN,
  saving_vs_agency DOUBLE
)
RETURN
WITH gap AS (SELECT * FROM ramsay_workforce.allocate.vw_open_gaps WHERE HoursAssignmentID=gap_id LIMIT 1),
staff AS (
  SELECT DISTINCT h.StaffNumber, concat(h.Forenames,' ',h.Surname) Name, h.PersonGradeShortName Grade,
         h.EmployeeTypeName EmployeeType, h.SiteID HomeSite, h.SiteLat lat, h.SiteLon lon,
         h.AgencyHourlyRate, h.PermHourlyRate
  FROM ramsay_workforce.allocate.enriched_hoursassignment h
  WHERE h.StaffNumber IS NOT NULL
    AND h.EmployeeTypeName <> 'Agency'   -- FIX 1: internal cover only
),
worked AS (
  SELECT StaffNumber, SUM(WorkHours) hours_last_7d FROM ramsay_workforce.allocate.vwah_hoursassignment
  WHERE CAST(ValidDate AS DATE) BETWEEN current_date()-7 AND current_date() GROUP BY StaffNumber
),
busy AS (
  SELECT DISTINCT StaffNumber FROM ramsay_workforce.allocate.vwah_hoursassignment
    WHERE CAST(ValidDate AS DATE)=(SELECT ShiftDate FROM gap) AND FulfillmentStatusName<>'Unfilled'
  UNION SELECT StaffNumber FROM ramsay_workforce.allocate.vwah_unavailability
    WHERE UnavailabilityState='Approved' AND (SELECT ShiftDate FROM gap) BETWEEN CAST(UnavailabilityStartDate AS DATE) AND CAST(UnavailabilityEndDate AS DATE)
)
SELECT s.StaffNumber, s.Name, s.Grade, s.EmployeeType, s.HomeSite,
  ROUND(6371*acos(least(1,cos(radians(g.SiteLat))*cos(radians(s.lat))*cos(radians(s.lon)-radians(g.SiteLon))+sin(radians(g.SiteLat))*sin(radians(s.lat)))),1) distance_km,
  coalesce(w.hours_last_7d,0) hours_last_7d,
  CASE s.EmployeeType WHEN 'Employee' THEN 1 WHEN 'Bank Only' THEN 2 ELSE 3 END contract_rank,
  -- FIX 2: use the gap's real shift length, not a hard-coded 8h
  (coalesce(w.hours_last_7d,0) + coalesce(g.PlannedAgencyHours,8)) <= 48 AS wtd_ok,
  ROUND(g.PlannedAgencyHours*(s.AgencyHourlyRate-s.PermHourlyRate),0) saving_vs_agency
FROM staff s CROSS JOIN gap g
LEFT JOIN worked w ON s.StaffNumber=w.StaffNumber
WHERE s.Grade=g.Grade AND s.StaffNumber NOT IN (SELECT StaffNumber FROM busy)
  AND (coalesce(w.hours_last_7d,0) + coalesce(g.PlannedAgencyHours,8)) <= 48
ORDER BY distance_km ASC, contract_rank ASC, hours_last_7d ASC
LIMIT 10
;
