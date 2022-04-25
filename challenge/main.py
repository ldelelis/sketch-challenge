import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import boto3
from psycopg2.pool import ThreadedConnectionPool


logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(name)s | %(threadName)s | %(message)s')

LEGACY_PATH_PREFIX = "image"
PRODUCTION_PATH_PREFIX = "avatar"

LEGACY_BUCKET_NAME = "legacy-s3"
PRODUCTION_BUCKET_NAME = "production-s3"

DB_CONN_STRING = os.getenv("DB_CONN_STRING")

S3_ENDPOINT_URL = os.getenv('S3_ENDPOINT_URL', 'http://localhost:9000')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin')
AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')

DEBUG = os.getenv('DEBUG', 'false').lower() == "true"


def get_db_connection_pool():
    # By default, postgres allows a maximum of 100 simultaneous connections
    # We can bypass this by either tuning postgresql.conf, or by adding a bouncer like `pgBouncer`
    conn_pool = ThreadedConnectionPool(50, 100, DB_CONN_STRING)

    return conn_pool


def main(s3):
    # Due to minimum connections, instanciation of a pool can fail as well as acquiring a new connection
    try:
        conn_pool = get_db_connection_pool()
    except:
        logging.exception("Error occurred while creating a connection to the database server")
        sys.exit(1)

    # Declare threaded function via closure. This allows the `s3` client and the connection pool to be usable via scope
    # Row is a tuple of (id, path)
    def callback(row):
        try:
            conn = conn_pool.getconn()
        except:
            logging.exception("Error occurred while creating a connection to the database server")
            return None
        cursor = conn.cursor()
        update_query = """
            UPDATE avatars
            SET path = REPLACE(path, %s, %s)
            WHERE id = %s
        """
        obj_id = row[0]
        obj_path = row[1]
        prod_obj_path = obj_path.replace(LEGACY_PATH_PREFIX, PRODUCTION_PATH_PREFIX, 1)

        # Directly copy the legacy object to the prod bucket with its new path
        try:
            s3.copy_object(
                Bucket=PRODUCTION_BUCKET_NAME,
                CopySource=f"{LEGACY_BUCKET_NAME}/{obj_path}",
                Key=prod_obj_path
            )
            cursor.execute(update_query, (LEGACY_PATH_PREFIX, PRODUCTION_PATH_PREFIX, obj_id,))
            if not DEBUG:
                conn.commit()
        except:
            logging.exception(f"Error occurred while trying to transfer {obj_path} across buckets")
            return None
        finally:
            conn_pool.putconn(conn)

        return obj_id
    try:
        conn = conn_pool.getconn()
    except:
        logging.exception("Error occurred while creating a connection to the database server")
        sys.exit(1)
    cursor = conn.cursor()

    read_query = f"""
        SELECT *
        FROM avatars
        WHERE path LIKE '{LEGACY_PATH_PREFIX}/%';
    """
    cursor.execute(read_query)
    fetched = cursor.rowcount

    tpool = ThreadPoolExecutor(max_workers=100)

    # A null value means transfer for a given object failed, so we don't update its record
    update_ids = tuple(avatar_id for avatar_id in tpool.map(callback, cursor) if avatar_id is not None)
    processed = len(update_ids)
    logging.info(f"Fetched {fetched} avatars")
    logging.info(f"Processed {processed} avatars")


if __name__ == "__main__":
    s3 = boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_DEFAULT_REGION
    )

    main(s3)
