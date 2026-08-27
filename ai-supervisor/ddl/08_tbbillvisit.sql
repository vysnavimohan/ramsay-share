CREATE TABLE ramsay_health.ops.tbbillvisit (
  SKeyBillVisit STRING COLLATE UTF8_BINARY,
  SKeyBillVisitAuthorisation STRING COLLATE UTF8_BINARY,
  SKeyBillPayorContractNHS STRING COLLATE UTF8_BINARY,
  SKeyBillPayorContractPMI BIGINT,
  SKeyBillPayorContractSelfPay BIGINT,
  SKeyPatient STRING COLLATE UTF8_BINARY,
  BillVisitID STRING COLLATE UTF8_BINARY,
  ReferralID STRING COLLATE UTF8_BINARY,
  AuthCode STRING COLLATE UTF8_BINARY,
  BillVisitDate STRING COLLATE UTF8_BINARY,
  VisitStatus STRING COLLATE UTF8_BINARY,
  VisitType STRING COLLATE UTF8_BINARY,
  HasPathology STRING COLLATE UTF8_BINARY,
  HasRadiology STRING COLLATE UTF8_BINARY)
USING delta
TBLPROPERTIES (
  'delta.checkpoint.writeStatsAsJson' = 'false',
  'delta.checkpoint.writeStatsAsStruct' = 'true',
  'delta.enableDeletionVectors' = 'true',
  'delta.feature.appendOnly' = 'supported',
  'delta.feature.deletionVectors' = 'supported',
  'delta.feature.invariants' = 'supported',
  'delta.minReaderVersion' = '3',
  'delta.minWriterVersion' = '7',
  'delta.parquet.compression.codec' = 'zstd',
  'delta.parquet.format.version' = '2.12.0',
  'delta.parquet.format.version.afe.internal' = '2.12.0')
;
