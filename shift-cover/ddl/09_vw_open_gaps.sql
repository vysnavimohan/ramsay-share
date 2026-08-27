CREATE VIEW allocate.vw_open_gaps (
  HoursAssignmentID,
  SiteID,
  SiteName,
  SitePostCode,
  SiteLat,
  SiteLon,
  Grade,
  GradeName,
  ShiftName,
  ShiftDate,
  ShiftType,
  ShiftStartDate,
  ShiftEndDate,
  GapReason,
  PlannedAgencyHours,
  agency_cost_if_unfilled,
  saving_if_filled_internally,
  ResourcingUnitShortName,
  PersonGradeLongName,
  RequiredGradeShortName,
  shift_hours,
  is_unfilled,
  absent_staff_name,
  absent_staff_number,
  absence_reason_group)
DEFAULT COLLATION UTF8_BINARY
WITH SCHEMA COMPENSATION
AS WITH sick AS (
  SELECT StaffNumber, CAST(UnavailabilityStartDate AS DATE) sd,
         CAST(UnavailabilityEndDate AS DATE) ed, UnavailabilityReasonGroup
  FROM ramsay_workforce.allocate.vwah_unavailability WHERE UnavailabilityState='Approved'
),
joined AS (
SELECT h.HoursAssignmentID, h.SiteID, h.SiteName, h.SitePostCode, h.SiteLat, h.SiteLon,
       h.PersonGradeShortName AS Grade, h.PostGradeLongName AS GradeName, h.ShiftName,
       CAST(h.ValidDate AS DATE) AS ShiftDate, h.ShiftType, h.ShiftStartDate, h.ShiftEndDate,
       CASE WHEN h.FulfillmentStatusName='Unfilled' THEN 'Unfilled Shift'
            ELSE concat('Sickness/Leave: ', h.Forenames,' ',h.Surname) END AS GapReason,
       h.PlannedAgencyHours,
       ROUND(h.PlannedAgencyHours*h.AgencyHourlyRate,0) AS agency_cost_if_unfilled,
       ROUND(h.PlannedAgencyHours*(h.AgencyHourlyRate-h.PermHourlyRate),0) AS saving_if_filled_internally,
       -- ---- v1 board UX pass: card-header fields ----
       -- Ward: "which ward" is the first thing a manager asks. 1,771/1,771 populated.
       h.ResourcingUnitShortName,
       h.PersonGradeLongName,        -- "Registered Nurse", not "RN"  [H3]
       h.RequiredGradeShortName,
       ROUND((unix_timestamp(h.ShiftEndDate)-unix_timestamp(h.ShiftStartDate))/3600.0,1) AS shift_hours,
       -- Let the UI branch on a boolean instead of parsing the GapReason string.
       (h.FulfillmentStatusName='Unfilled') AS is_unfilled,
       -- Populated ONLY for a genuine roster absence, where the roster itself carries the
       -- StaffNumber. NEVER inferred: an Unfilled post has nobody to name, and guessing by
       -- site+grade+date gives 2.15 candidates/shift (worst 9). See SPEC §2 / [H7].
       CASE WHEN h.FulfillmentStatusName='Unfilled' THEN NULL
            ELSE concat(h.Forenames,' ',h.Surname) END AS absent_staff_name,
       CASE WHEN h.FulfillmentStatusName='Unfilled' THEN NULL
            ELSE h.StaffNumber END AS absent_staff_number,
       CASE WHEN h.FulfillmentStatusName='Unfilled' THEN NULL
            ELSE k.UnavailabilityReasonGroup END AS absence_reason_group,
       -- ONE row per gap. A nurse can hold two overlapping approved absences (e.g.
       -- AnnualLeave AND Sickness covering the same day), and the LEFT JOIN then emits a
       -- gap row per absence — 9 gaps in the 7d window fanned out into DUPLICATE CARDS.
       -- Pre-existing bug, caught by the rows-vs-distinct guard below. Deduped on the gap
       -- itself (not the absence window) so any overlap shape collapses to one card;
       -- Sickness wins the tie because it is the operationally urgent reason to show.
       row_number() OVER (
         PARTITION BY h.HoursAssignmentID
         ORDER BY CASE WHEN k.UnavailabilityReasonGroup='Sickness' THEN 0 ELSE 1 END,
                  k.UnavailabilityReasonGroup) AS _rn
FROM ramsay_workforce.allocate.enriched_hoursassignment h
LEFT JOIN sick k ON h.StaffNumber=k.StaffNumber
                AND CAST(h.ValidDate AS DATE) BETWEEN k.sd AND k.ed
WHERE CAST(h.ValidDate AS DATE) >= current_date()
  AND (h.FulfillmentStatusName='Unfilled' OR k.StaffNumber IS NOT NULL)
)
SELECT * EXCEPT (_rn) FROM joined WHERE _rn=1
;
