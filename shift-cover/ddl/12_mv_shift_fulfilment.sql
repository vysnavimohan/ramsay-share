CREATE VIEW ramsay_workforce.allocate.mv_shift_fulfilment (
  Site,
  SiteID,
  Grade,
  EmployeeType,
  ShiftType,
  FulfillmentStatus,
  ValidDate,
  total_shifts,
  unfilled_shifts,
  fill_rate,
  planned_agency_hours,
  actual_agency_hours,
  agency_cost,
  equivalent_perm_cost,
  agency_premium,
  wte_total)
WITH METRICS
LANGUAGE YAML
AS
$$

version: 0.1
source: ramsay_workforce.allocate.enriched_hoursassignment
dimensions:
  - name: Site
    expr: SiteName
  - name: SiteID
    expr: SiteID
  - name: Grade
    expr: PersonGradeShortName
  - name: EmployeeType
    expr: EmployeeTypeName
  - name: ShiftType
    expr: ShiftType
  - name: FulfillmentStatus
    expr: FulfillmentStatusName
  - name: ValidDate
    expr: CAST(ValidDate AS DATE)
measures:
  - name: total_shifts
    expr: COUNT(1)
  - name: unfilled_shifts
    expr: SUM(CASE WHEN FulfillmentStatusName='Unfilled' THEN 1 ELSE 0 END)
  - name: fill_rate
    expr: ROUND(100.0*SUM(CASE WHEN FulfillmentStatusName='Filled' THEN 1 ELSE 0 END)/COUNT(1),1)
  - name: planned_agency_hours
    expr: SUM(PlannedAgencyHours)
  - name: actual_agency_hours
    expr: SUM(ActualAgencyHours)
  - name: agency_cost
    expr: ROUND(SUM(PlannedAgencyHours*AgencyHourlyRate),0)
  - name: equivalent_perm_cost
    expr: ROUND(SUM(PlannedAgencyHours*PermHourlyRate),0)
  - name: agency_premium
    expr: ROUND(SUM(PlannedAgencyHours*(AgencyHourlyRate-PermHourlyRate)),0)
  - name: wte_total
    expr: ROUND(SUM(CAST(WTE AS DOUBLE)),1)
$$
;
