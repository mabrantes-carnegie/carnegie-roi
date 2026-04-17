environment = "dev"

# Cloud Run
min_instances = 0
max_instances = 1
cpu           = "1"
memory        = "512Mi"

# Use materialized tables in dbt_mlima for testing
use_materialized = true
