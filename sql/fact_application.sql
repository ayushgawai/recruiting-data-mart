-- fact_application
CREATE OR REPLACE TABLE mart.fact_application AS
SELECT application_id, candidate_id, requisition_id, source, applied_date::DATE AS applied_date
FROM raw.applications;
