CREATE VIEW ops.vw_case_ledger (
  SiteIDInt,
  SiteID,
  SiteName,
  ServiceName,
  HRGCode,
  ProcedureGroup,
  CaseDate,
  Cases,
  Revenue)
DEFAULT COLLATION UTF8_BINARY
WITH SCHEMA COMPENSATION
AS SELECT CAST(i.SiteID AS INT) AS SiteIDInt,
       LPAD(CAST(CAST(i.SiteID AS INT) AS STRING), 4, '0') AS SiteID,
       d.SiteName, r.ServiceName, i.HRGCode, i.ProcedureGroup,
       TO_DATE(b.BillVisitDate) AS CaseDate,
       COUNT(*) AS Cases,
       SUM(CAST(i.InvoiceValue AS DOUBLE)) AS Revenue
FROM ramsay_health.ops.tbinvoice i
JOIN ramsay_health.ops.tbbillvisit b ON i.VisitID = b.BillVisitID
JOIN ramsay_health.ops.tbreferrals r ON b.ReferralID = r.ReferralID
LEFT JOIN ramsay_health.ops.dim_site d ON LPAD(CAST(CAST(i.SiteID AS INT) AS STRING), 4, '0') = d.SiteID
WHERE i.PrimaryCCSDCode <> 'null' AND i.InvoiceCancelled = 'N'
GROUP BY CAST(i.SiteID AS INT),
         LPAD(CAST(CAST(i.SiteID AS INT) AS STRING), 4, '0'),
         d.SiteName, r.ServiceName, i.HRGCode, i.ProcedureGroup, TO_DATE(b.BillVisitDate)
;
