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

def delete_existing_rows(conn: sqlite3.Connection, start_date: str, end_date: str) -> int:
    cursor = conn.execute(
        """
        DELETE FROM mart_daily_summary
        WHERE trip_date BETWEEN ? AND ?
        """,
        (start_date, end_date)
    )
    return cursor.rowcount

def insert_aggregated_rows(conn: sqlite3.Connection, start_date: str, end_date: str) -> int:
    cursor = conn.execute(
        """
        INSERT INTO mart_daily_summary (
            trip_date,
            trip_count,
            total_fare,
            total_revenue,
            avg_fare,
            avg_distance,
            avg_passengers,
            avg_duration_min
        )
        SELECT
            trip_date,
            COUNT(*) AS trip_count,
            SUM(CAST(fare_amount AS REAL)) AS total_fare,
            NULL AS total_revenue,
            NULL AS avg_fare,
            NULL AS avg_distance,
            AVG(CAST(passenger_count AS REAL)) AS avg_passengers,
            NULL AS avg_duration_min
        FROM staging_trips
        WHERE trip_date BETWEEN ? AND ?
        GROUP BY trip_date
        """,
        (start_date, end_date)
    )
    return cursor.rowcount

def main() -> None:
    logging.info("Opening database at %s", DB_PATH)
    if not DB_PATH.is_file():
        logging.error("Database file not found: %s", DB_PATH)
        return

    conn = sqlite3.connect(str(DB_PATH))
    try:
        logging.info("Starting transaction")
        conn.execute("BEGIN")

        deleted = delete_existing_rows(conn, MISSING_START, MISSING_END)
        logging.info("Rows deleted from mart_daily_summary: %d", deleted)

        inserted = insert_aggregated_rows(conn, MISSING_START, MISSING_END)
        logging.info("Rows inserted into mart_daily_summary: %d", inserted)

        conn.commit()
        logging.info("Transaction committed successfully")
    except Exception as e:
        logging.exception("Error occurred, rolling back transaction: %s", e)
        conn.rollback()
        logging.info("Transaction rolled back")
    finally:
        conn.close()
        logging.info("Database connection closed")

if __name__ == "__main__":
    main()