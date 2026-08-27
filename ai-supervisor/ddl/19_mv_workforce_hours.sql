CREATE VIEW ramsay_health.ops.mv_workforce_hours (
  Site,
  Grade,
  Grade Description,
  Employee Type,
  Shift Type,
  Shift Date,
  Shifts,
  Staff,
  Total Hours,
  Filled Shifts,
  Unfilled Shifts,
  Fill Rate)
COMMENT 'Workforce hours, fill rate, headcount by grade/site'
WITH METRICS
LANGUAGE YAML
AS
$$
version: 1.1

source: ramsay_health.ops.vwah_hoursassignment

comment: "Workforce hours, fill rate, headcount by grade/site"

dimensions:
  - name: Site
    expr: SiteID

  - name: Grade
    expr: PersonGradeTypeName

  - name: Grade Description
    expr: PostGradeLongName

  - name: Employee Type
    expr: EmployeeTypeName

  - name: Shift Type
    expr: ShiftType

  - name: Shift Date
    expr: CAST(CAST(ValidDate AS TIMESTAMP) AS DATE)

measures:
  - name: Shifts
    expr: COUNT(1)

  - name: Staff
    expr: COUNT(DISTINCT StaffNumber)

  - name: Total Hours
    expr: SUM(CAST(WorkHours AS DOUBLE))

  - name: Filled Shifts
    expr: SUM(CASE WHEN FulfillmentStatusName = 'Filled' THEN 1 ELSE 0 END)

  - name: Unfilled Shifts
    expr: SUM(CASE WHEN FulfillmentStatusName = 'Unfilled Shift' THEN 1 ELSE 0 END)

  - name: Fill Rate
    expr: SUM(CASE WHEN FulfillmentStatusName = 'Filled' THEN 1.0 ELSE 0 END) / COUNT(1)
$$
;
