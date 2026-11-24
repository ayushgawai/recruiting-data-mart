-- dim_requisition
CREATE OR REPLACE TABLE mart.dim_requisition AS
SELECT requisition_id, department, title, opened_date::DATE AS opened_date FROM raw.requisitions;
