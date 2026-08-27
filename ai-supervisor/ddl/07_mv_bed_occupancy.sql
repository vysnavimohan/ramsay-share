CREATE VIEW ramsay_health.ops.mv_bed_occupancy (
  Site,
  Bed Date,
  Avg Occupancy,
  Beds Occupied,
  Beds Available,
  Admissions,
  Discharges)
COMMENT 'Bed occupancy & flow'
WITH METRICS
LANGUAGE YAML
AS
$$
version: 1.1

source: ramsay_health.ops.vw_bed_occupancy

comment: Bed occupancy & flow

dimensions:
  - name: Site
    expr: SiteName

  - name: Bed Date
    expr: BedDate

measures:
  - name: Avg Occupancy
    expr: AVG(OccupancyPct)

  - name: Beds Occupied
    expr: SUM(BedsOccupied)

  - name: Beds Available
    expr: SUM(BedsAvailable)

  - name: Admissions
    expr: SUM(Admissions)

  - name: Discharges
    expr: SUM(Discharges)
$$
;
