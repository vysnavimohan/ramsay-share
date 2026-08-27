CREATE MATERIALIZED VIEW `ramsay_workforce`.`allocate`.`mv_gap_candidates` (
  HoursAssignmentID BIGINT,
  ShiftDate DATE,
  rnk INT,
  StaffNumber STRING COLLATE UTF8_BINARY,
  Name STRING COLLATE UTF8_BINARY,
  EmployeeType STRING COLLATE UTF8_BINARY,
  distance_km DOUBLE,
  hours_last_7d DOUBLE,
  saving DOUBLE,
  agency_cost DOUBLE)
COMMENT 'Top-3 ranked compliant internal cover candidates per open gap (45d horizon). Precomputed: the equivalent live query cost ~5.1s for a 7d window.'
SCHEDULE EVERY 1 HOURS
AS WITH g AS (
  SELECT HoursAssignmentID, SiteName, Grade, ShiftDate, ShiftName,
         SiteLat, SiteLon, PlannedAgencyHours,
         agency_cost_if_unfilled AS agency_cost,
         saving_if_filled_internally AS saving
  FROM ramsay_workforce.allocate.vw_open_gaps
  WHERE ShiftDate BETWEEN current_date() AND current_date()+45
),
cand AS (
  SELECT DISTINCT StaffNumber, concat(Forenames,' ',Surname) Name,
         PersonGradeShortName Grade, EmployeeTypeName EmployeeType,
         SiteLat lat, SiteLon lon
  FROM ramsay_workforce.allocate.enriched_hoursassignment
  WHERE StaffNumber IS NOT NULL AND EmployeeTypeName<>'Agency'
),
worked AS (
  SELECT StaffNumber, SUM(WorkHours) h FROM ramsay_workforce.allocate.vwah_hoursassignment
  WHERE CAST(ValidDate AS DATE) BETWEEN current_date()-7 AND current_date()
  GROUP BY StaffNumber
),
busy AS (
  SELECT DISTINCT StaffNumber, CAST(ValidDate AS DATE) d
  FROM ramsay_workforce.allocate.vwah_hoursassignment
  WHERE FulfillmentStatusName<>'Unfilled' AND StaffNumber IS NOT NULL
    AND CAST(ValidDate AS DATE) BETWEEN current_date() AND current_date()+45
),
away AS (
  SELECT DISTINCT StaffNumber, CAST(UnavailabilityStartDate AS DATE) sd,
         CAST(UnavailabilityEndDate AS DATE) ed
  FROM ramsay_workforce.allocate.vwah_unavailability WHERE UnavailabilityState='Approved'
),
pairs AS (
  SELECT g.HoursAssignmentID, g.SiteName, g.Grade, g.ShiftDate, g.ShiftName,
         g.agency_cost, g.saving,
         c.StaffNumber, c.Name, c.EmployeeType,
         ROUND(6371*acos(least(1,cos(radians(g.SiteLat))*cos(radians(c.lat))
              *cos(radians(c.lon)-radians(g.SiteLon))
              +sin(radians(g.SiteLat))*sin(radians(c.lat)))),1) distance_km,
         coalesce(w.h,0) hours_last_7d,
         CASE c.EmployeeType WHEN 'Employee' THEN 1 WHEN 'Bank Only' THEN 2 ELSE 3 END contract_rank
  FROM g
  JOIN cand c ON c.Grade=g.Grade
  LEFT JOIN worked w ON c.StaffNumber=w.StaffNumber
  -- WTD uses the gap's ACTUAL shift length; a hard-coded 8 passed a candidate on 40h
  -- as compliant for a 12h night shift (40+12=52 > 48).
  WHERE (coalesce(w.h,0)+coalesce(g.PlannedAgencyHours,8)) <= 48
    -- Anti-joins, not correlated NOT IN: Spark rejects a subquery predicate that mixes
    -- outer and local refs (UNSUPPORTED_SUBQUERY_EXPRESSION_CATEGORY), and this shape
    -- is what makes the MV cheap enough to precompute.
    AND NOT EXISTS (SELECT 1 FROM busy b
                    WHERE b.StaffNumber=c.StaffNumber AND b.d=g.ShiftDate)
    AND NOT EXISTS (SELECT 1 FROM away a
                    WHERE a.StaffNumber=c.StaffNumber
                      AND g.ShiftDate BETWEEN a.sd AND a.ed)
),
ranked AS (
  SELECT *, row_number() OVER (PARTITION BY HoursAssignmentID
           ORDER BY contract_rank ASC, distance_km ASC, hours_last_7d ASC) rnk
  FROM pairs
)
SELECT HoursAssignmentID, ShiftDate, rnk, StaffNumber, Name, EmployeeType,
       distance_km, hours_last_7d, saving, agency_cost
FROM ranked WHERE rnk<=3
;
