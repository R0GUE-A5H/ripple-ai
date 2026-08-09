graph [
  directed 1
  node [
    id 0
    label "urn:li:dataset:(urn:li:dataPlatform:sqlite,nyc_taxi_pipeline.main.mart_daily_summary,PROD)"
    name "mart_daily_summary"
    type "DATASET"
  ]
  node [
    id 1
    label "urn:li:dataset:(urn:li:dataPlatform:sqlite,nyc_taxi_pipeline.main.raw_trips,PROD)"
    name "raw_trips"
    type "DATASET"
  ]
  node [
    id 2
    label "urn:li:dataset:(urn:li:dataPlatform:sqlite,nyc_taxi_pipeline.main.staging_trips,PROD)"
    name "staging_trips"
    type "DATASET"
  ]
  node [
    id 3
    label "urn:li:dashboard:(superset,cfo_revenue_dashboard)"
    name "CFO Revenue Dashboard"
    type "DASHBOARD"
  ]
  node [
    id 4
    label "urn:li:dataset:(urn:li:dataPlatform:sqlite,nyc_taxi_pipeline.main.v_daily_from_staging,PROD)"
    name "v_daily_from_staging"
    type "DATASET"
  ]
  node [
    id 5
    label "urn:li:dataset:(urn:li:dataPlatform:sqlite,nyc_taxi_pipeline.main.v_staging_from_raw,PROD)"
    name "v_staging_from_raw"
    type "DATASET"
  ]
  edge [
    source 0
    target 3
  ]
  edge [
    source 1
    target 2
  ]
  edge [
    source 1
    target 5
  ]
  edge [
    source 2
    target 0
  ]
  edge [
    source 2
    target 4
  ]
]
