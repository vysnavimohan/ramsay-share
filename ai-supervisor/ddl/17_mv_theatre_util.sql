CREATE VIEW ramsay_health.ops.mv_theatre_util (
  Site,
  Specialty,
  Session Date,
  Avg Utilisation,
  Cases Completed,
  Cases Scheduled,
  Cancellations,
  Sessions)
COMMENT 'Theatre utilisation & throughput'
WITH METRICS
LANGUAGE YAML
AS
$$
version: 1.1

source: ramsay_health.ops.vw_theatre_throughput

comment: Theatre utilisation & throughput

dimensions:
  - name: Site
    expr: SiteName

  - name: Specialty
    expr: Specialty

  - name: Session Date
    expr: SessionDate

measures:
  - name: Avg Utilisation
    expr: AVG(UtilisationPct)

  - name: Cases Completed
    expr: SUM(CasesCompleted)

  - name: Cases Scheduled
    expr: SUM(CasesScheduled)

  - name: Cancellations
    expr: SUM(OnDayCancellations)

  - name: Sessions
    expr: COUNT(1)
$$
;
