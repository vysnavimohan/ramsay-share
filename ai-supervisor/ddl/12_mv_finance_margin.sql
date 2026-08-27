CREATE VIEW ramsay_health.ops.mv_finance_margin (
  Site,
  Channel,
  Procedure Group,
  Service,
  Visit Type,
  Invoice Date,
  Revenue,
  Cost,
  Margin,
  Margin Pct,
  Invoices,
  Avg Invoice Value)
COMMENT 'Revenue, cost & margin by channel / procedure / site'
WITH METRICS
LANGUAGE YAML
AS
$$
version: 1.1

source: ramsay_health.ops.vw_finance_base

comment: "Revenue, cost & margin by channel / procedure / site"

dimensions:
  - name: Site
    expr: SiteName

  - name: Channel
    expr: InvoiceChannel

  - name: Procedure Group
    expr: ProcedureGroup

  - name: Service
    expr: ServiceName

  - name: Visit Type
    expr: VisitType

  - name: Invoice Date
    expr: InvoiceDate

measures:
  - name: Revenue
    expr: SUM(Revenue)

  - name: Cost
    expr: SUM(Cost)

  - name: Margin
    expr: SUM(Margin)

  - name: Margin Pct
    expr: "SUM(Margin) / NULLIF(SUM(Revenue), 0) * 100"

  - name: Invoices
    expr: COUNT(1)

  - name: Avg Invoice Value
    expr: AVG(Revenue)
$$
;
