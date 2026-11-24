-- fact_stage_event: partitioned by stage in Athena/S3 (stage=<stage>/),
-- clustered/sort-key on (stage, event_date) in Snowflake/Redshift.
CREATE OR REPLACE TABLE mart.fact_stage_event AS
SELECT application_id, candidate_id, requisition_id, stage, source, event_date::DATE AS event_date
FROM raw.stage_events;
-- Redshift: DISTKEY(application_id) SORTKEY(stage, event_date)
-- Snowflake: CLUSTER BY (stage, event_date)
