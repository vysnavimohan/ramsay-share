CREATE TABLE ramsay_health.ops.fact_diagnostic_slot (
  SiteID STRING COLLATE UTF8_BINARY,
  Modality STRING COLLATE UTF8_BINARY,
  SlotDate STRING COLLATE UTF8_BINARY,
  Rooms BIGINT,
  SlotsCapacity BIGINT,
  SlotsBooked BIGINT,
  SlotsAvailable BIGINT,
  UtilisationPct DOUBLE,
  DNACount BIGINT)
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
