CREATE TABLE ramsay_health.ops.dim_site (
  SiteID STRING COLLATE UTF8_BINARY,
  SiteName STRING COLLATE UTF8_BINARY,
  Beds BIGINT,
  Theatres BIGINT,
  PostCode STRING COLLATE UTF8_BINARY,
  Latitude DOUBLE,
  Longitude DOUBLE)
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
