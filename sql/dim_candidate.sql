-- dim_candidate (Snowflake/Redshift style; mirrors src/recmart/models.py)
CREATE OR REPLACE TABLE mart.dim_candidate AS
SELECT candidate_id, source, created_date::DATE AS created_date
FROM raw.candidates QUALIFY ROW_NUMBER() OVER (PARTITION BY candidate_id ORDER BY created_date DESC) = 1;
