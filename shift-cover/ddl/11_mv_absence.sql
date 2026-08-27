CREATE VIEW ramsay_workforce.allocate.mv_absence (
  Site,
  SiteID,
  Grade,
  ReasonGroup,
  State,
  ValidDate,
  absence_events,
  work_minutes_missed,
  sickness_hours,
  lost_hours,
  rtw_completion_rate)
WITH METRICS
LANGUAGE YAML
AS
$$

version: 0.1
source: |
  SELECT * FROM ramsay_workforce.allocate.enriched_unavailability
  WHERE UnavailabilityState = 'Approved' AND coalesce(DeletedFlag, false) = false
dimensions:
  - name: Site
    expr: SiteName
  - name: SiteID
    expr: SiteID
  - name: Grade
    expr: PersonGradeShortName
  - name: ReasonGroup
    expr: UnavailabilityReasonGroup
  - name: State
    expr: UnavailabilityState
  - name: ValidDate
    expr: CAST(ValidDate AS DATE)
measures:
  - name: absence_events
    expr: COUNT(1)
  - name: work_minutes_missed
    expr: SUM(WORKMINUTESMISSED)
  - name: sickness_hours
    expr: ROUND(SUM(SicknessHours),1)
  - name: lost_hours
    expr: ROUND(SUM(LostHours),1)
  - name: rtw_completion_rate
    expr: ROUND(100.0*SUM(ReturnToWorkInterviewComplete)/NULLIF(SUM(CASE WHEN UnavailabilityReasonGroup='Sickness' THEN 1 ELSE 0 END),0),1)
$$
;
