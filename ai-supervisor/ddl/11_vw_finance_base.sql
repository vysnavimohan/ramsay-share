CREATE VIEW ops.vw_finance_base (
  InvoiceNumber,
  VisitID,
  ReferralID,
  SiteID,
  SiteName,
  InvoiceChannel,
  ProcedureGroup,
  HRGDescription,
  ProcedureDescription,
  Revenue,
  Cost,
  Margin,
  InvoiceDate,
  VisitType,
  ServiceName,
  PayorType)
DEFAULT COLLATION UTF8_BINARY
WITH SCHEMA COMPENSATION
AS SELECT i.InvoiceNumber, i.VisitID, b.ReferralID, i.SiteID, d.SiteName, i.InvoiceChannel,
 i.ProcedureGroup, i.HRGDescription, i.ProcedureDescription,
 CAST(i.InvoiceValue AS DOUBLE) AS Revenue,
 CAST((CASE i.HRGCode WHEN 'HB12C' THEN 4600 WHEN 'HB22C' THEN 4500 WHEN 'HB99Z' THEN 1500 WHEN 'BZ34C' THEN 650 WHEN 'FZ38A' THEN 520 WHEN 'LB54A' THEN 3400 WHEN 'FZ01A' THEN 1300 WHEN 'CZ01Z' THEN 950 WHEN 'MA07Z' THEN 800 WHEN 'RD01A' THEN 180 ELSE 0 END)*CASE WHEN b.VisitType='Outpatient' THEN 0.1 ELSE 1 END AS DOUBLE) AS Cost,
 CAST(i.InvoiceValue AS DOUBLE)-CAST((CASE i.HRGCode WHEN 'HB12C' THEN 4600 WHEN 'HB22C' THEN 4500 WHEN 'HB99Z' THEN 1500 WHEN 'BZ34C' THEN 650 WHEN 'FZ38A' THEN 520 WHEN 'LB54A' THEN 3400 WHEN 'FZ01A' THEN 1300 WHEN 'CZ01Z' THEN 950 WHEN 'MA07Z' THEN 800 WHEN 'RD01A' THEN 180 ELSE 0 END)*CASE WHEN b.VisitType='Outpatient' THEN 0.1 ELSE 1 END AS DOUBLE) AS Margin,
 TO_DATE(i.InvoiceCreatedDate,'yyyyMMdd') AS InvoiceDate, b.VisitType, r.ServiceName, r.PayorType
FROM ramsay_health.ops.tbinvoice i JOIN ramsay_health.ops.tbbillvisit b ON i.VisitID=b.BillVisitID
JOIN ramsay_health.ops.tbreferrals r ON b.ReferralID=r.ReferralID
LEFT JOIN ramsay_health.ops.dim_site d ON CAST(i.SiteID AS STRING)=TRY_CAST(CAST(d.SiteID AS INT) AS STRING)
WHERE i.InvoiceCancelled='N'
;
