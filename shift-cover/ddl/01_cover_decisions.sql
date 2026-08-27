CREATE TABLE ramsay_workforce.allocate.cover_decisions (
  decision_id STRING COLLATE UTF8_BINARY,
  HoursAssignmentID BIGINT,
  SiteName STRING COLLATE UTF8_BINARY,
  Grade STRING COLLATE UTF8_BINARY,
  ShiftDate DATE,
  assigned_staff STRING COLLATE UTF8_BINARY,
  assigned_type STRING COLLATE UTF8_BINARY,
  distance_km DOUBLE,
  saving_gbp DOUBLE,
  rationale STRING COLLATE UTF8_BINARY,
  decided_by STRING COLLATE UTF8_BINARY,
  decided_at TIMESTAMP,
  status STRING COLLATE UTF8_BINARY,
  outreach_status STRING COLLATE UTF8_BINARY,
  resolution_mode STRING COLLATE UTF8_BINARY,
  assigned_staff_number STRING COLLATE UTF8_BINARY COMMENT 'StaffNumber — names are not unique (108 shared names); key outreach state on this')
USING delta
DEFAULT COLLATION UTF8_BINARY
TBLPROPERTIES (
  'delta.checkpoint.writeStatsAsJson' = 'false',
  'delta.checkpoint.writeStatsAsStruct' = 'true',
  'delta.enableDeletionVectors' = 'true',
  'delta.enableRowTracking' = 'true',
  'delta.feature.appendOnly' = 'supported',
  'delta.feature.deletionVectors' = 'supported',
  'delta.feature.domainMetadata' = 'supported',
  'delta.feature.invariants' = 'supported',
  'delta.feature.rowTracking' = 'supported',
  'delta.minReaderVersion' = '3',
  'delta.minWriterVersion' = '7',
  'delta.parquet.compression.codec' = 'zstd',
  'delta.parquet.format.version' = '2.12.0',
  'delta.parquet.format.version.afe.internal' = '2.12.0')
;
