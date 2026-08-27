CREATE TABLE ramsay_health.ops.fact_theatre_session (
  SessionID STRING COLLATE UTF8_BINARY,
  TheatreID STRING COLLATE UTF8_BINARY,
  SiteID STRING COLLATE UTF8_BINARY,
  SessionDate STRING COLLATE UTF8_BINARY,
  SessionSlot STRING COLLATE UTF8_BINARY,
  Specialty STRING COLLATE UTF8_BINARY,
  PlannedMinutes BIGINT,
  UsedMinutes BIGINT,
  UtilisationPct DOUBLE,
  CasesScheduled BIGINT,
  CasesCompleted BIGINT,
  OnDayCancellations BIGINT)
USING delta
DEFAULT COLLATION UTF8_BINARY
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
