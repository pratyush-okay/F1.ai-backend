DEV_CONN=postgresql://postgres.ynuccztzlfhftvupoxzh:formula1.ainicksimonpanda@aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres
PROD_CONN=postgresql://postgres.jqqcvfptjwwgikjkroku:formula1.ainicksimonpanda@aws-0-us-east-2.pooler.supabase.com:5432/postgres

pg_dump "$DEV_CONN" --schema=public --no-owner --no-privileges --data-only > data.sql
psql "$PROD_CONN" < data.sql  