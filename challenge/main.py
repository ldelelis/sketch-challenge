import os
from concurrent.futures import ThreadPoolExecutor

import boto3
import psycopg2

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


def get_db_connection():
    # Let exceptions propagate. We can't operate without a db connection so we shouldn't handle this
    connection = psycopg2.connect(DB_CONN_STRING)

    return connection


def main(s3):
    # Declare threaded function via closure. This allows the `s3` client to be usable via scope
    def callback(row):
        # Row is a tuple of (id, path)
        obj_id = row[0]
        obj_path = row[1]
        prod_obj_path = obj_path.replace(LEGACY_PATH_PREFIX, PRODUCTION_PATH_PREFIX, 1)

        # Directly copy the legacy object to the prod bucket with its new path
        s3.copy_object(
            Bucket=PRODUCTION_BUCKET_NAME,
            CopySource=f"{LEGACY_BUCKET_NAME}/{obj_path}",
            Key=prod_obj_path
        )

        return obj_id

    conn = get_db_connection()
    cursor = conn.cursor()

    read_query = f"SELECT * FROM avatars WHERE path LIKE '{LEGACY_PATH_PREFIX}/%';"
    update_query = """
        UPDATE avatars
        SET path = REPLACE(path, %s, %s)
        WHERE id IN %s
    """
    cursor.execute(read_query)

    tpool = ThreadPoolExecutor(max_workers=100)

    update_ids = tuple(avatar_id for avatar_id in tpool.map(callback, cursor))

    cursor.execute(update_query, (LEGACY_PATH_PREFIX, PRODUCTION_PATH_PREFIX, update_ids,))

    # For benchmarking purposes, only commit on non-debug runs
    if not DEBUG:
        conn.commit()


if __name__ == "__main__":
    s3 = boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_DEFAULT_REGION
    )

    main(s3)
