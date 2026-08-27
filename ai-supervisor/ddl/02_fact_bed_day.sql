CREATE TABLE ramsay_health.ops.fact_bed_day (
  SiteID STRING COLLATE UTF8_BINARY,
  BedDate STRING COLLATE UTF8_BINARY,
  BedsAvailable BIGINT,
  BedsOccupied BIGINT,
  OccupancyPct DOUBLE,
  Admissions BIGINT,
  Discharges BIGINT)
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
