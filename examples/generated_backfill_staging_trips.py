import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from contextlib import closing

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()]
)

DB_PATH = Path(r"D:\Projects\datahub_hackathon\nyc-taxi\nyc_taxi_pipeline.db")
MISSING_START = "2016-03-02"
MISSING_END = "2016-03-10"

def main() -> None:
    logging.info("Opening database at %s", DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("BEGIN")
        logging.info("Transaction started")

        # Delete existing rows in the missing date range
        delete_sql = """
            DELETE FROM staging_trips
            WHERE trip_date BETWEEN ? AND ?
        """
        cur = conn.execute(delete_sql, (MISSING_START, MISSING_END))
        rows_deleted = cur.rowcount
        logging.info("Rows deleted from staging_trips: %d", rows_deleted)

        # Insert recomputed rows from raw_trips
        insert_sql = """
            INSERT INTO staging_trips (
                VendorID,
                tpep_pickup_datetime,
                tpep_dropoff_datetime,
                passenger_count,
                trip_distance,
                pickup_longitude,
                pickup_latitude,
                RateCodeID,
                store_and_fwd_flag,
                dropoff_longitude,
                dropoff_latitude,
                payment_type,
                fare_amount,
                extra,
                mta_tax,
                tip_amount,
                tolls_amount,
                improvement_surcharge,
                total_amount,
                trip_date,
                trip_duration_min,
                pipeline_status
            )
            SELECT
                VendorID,
                tpep_pickup_datetime,
                tpep_dropoff_datetime,
                passenger_count,
                trip_distance,
                pickup_longitude,
                pickup_latitude,
                RateCodeID,
                store_and_fwd_flag,
                dropoff_longitude,
                dropoff_latitude,
                payment_type,
                fare_amount,
                extra,
                mta_tax,
                tip_amount,
                tolls_amount,
                improvement_surcharge,
                total_amount,
                date(tpep_pickup_datetime) AS trip_date,
                (julianday(tpep_dropoff_datetime) - julianday(tpep_pickup_datetime)) * 24 * 60 AS trip_duration_min,
                NULL AS pipeline_status
            FROM raw_trips
            WHERE
                date(tpep_pickup_datetime) BETWEEN ? AND ?
                AND tpep_pickup_datetime IS NOT NULL
                AND tpep_dropoff_datetime IS NOT NULL
                AND tpep_pickup_datetime <> ''
                AND tpep_dropoff_datetime <> ''
        """
        cur = conn.execute(insert_sql, (MISSING_START, MISSING_END))
        rows_inserted = cur.rowcount
        logging.info("Rows inserted into staging_trips: %d", rows_inserted)

        conn.commit()
        logging.info("Commit successful")
    except Exception as e:
        logging.exception("Error occurred, rolling back transaction")
        conn.rollback()
    finally:
        conn.close()
        logging.info("Database connection closed")

if __name__ == "__main__":
    main()