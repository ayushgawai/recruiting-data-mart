-- Funnel: distinct applications per stage, in pipeline order
SELECT stage, COUNT(DISTINCT application_id) AS applications
FROM mart.fact_stage_event GROUP BY stage;

-- Time-to-stage: avg days from applied to first reaching each stage
SELECT stage, AVG(DATEDIFF(day, applied_date, first_event_date)) AS avg_days, COUNT(*) AS n
FROM (SELECT f.application_id, f.stage, MIN(f.event_date) AS first_event_date, a.applied_date
      FROM mart.fact_stage_event f JOIN mart.fact_application a USING (application_id)
      GROUP BY 1,2,4) t GROUP BY stage;

-- Source ROI rollup (cost_per_application is an illustrative config, see queries.py)
SELECT a.source, COUNT(DISTINCT a.application_id) AS applications,
       COUNT(DISTINCT CASE WHEN f.stage='hired' THEN a.application_id END) AS hires
FROM mart.fact_application a LEFT JOIN mart.fact_stage_event f USING (application_id)
GROUP BY a.source ORDER BY hires DESC;
