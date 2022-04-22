import io
import os

import boto3
import psycopg2

# TODO: extract these to env variables
LEGACY_PATH_PREFIX = "image"
PRODUCTION_PATH_PREFIX = "avatar"

DB_USER = "sketch"
DB_PASS = "sketch"
DB_NAME = "production-db"
DB_HOST = "localhost"
DB_PORT = "5432"

LEGACY_BUCKET_NAME = "legacy-s3"
PRODUCTION_BUCKET_NAME = "production-s3"

S3_ENDPOINT_URL = os.getenv('S3_ENDPOINT_URL', 'http://localhost:9000')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin')
AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')

DEBUG = os.getenv('DEBUG', 'false').lower() == "true"


def get_db_connection():
    dsn = f"dbname={DB_NAME} user={DB_USER} password={DB_PASS} host={DB_HOST} port={DB_PORT}"
    # TODO: exceptions?
    connection = psycopg2.connect(dsn)

    return connection


def main(s3):
    conn = get_db_connection()
    cursor = conn.cursor()
    update_ids = []

    read_query = f"SELECT * FROM avatars WHERE path LIKE '{LEGACY_PATH_PREFIX}/%';"
    update_query = """
        UPDATE avatars
        SET path = REPLACE(path, %s, %s)
        WHERE id IN %s
    """
    cursor.execute(read_query)

    # Tuples of (id, path)
    for row in cursor:
        obj_id = row[0]
        obj_path = row[1]

        # TODO: check failure cases?
        legacy_obj_response = s3.get_object(Bucket=LEGACY_BUCKET_NAME, Key=obj_path)
        legacy_obj = legacy_obj_response['Body'].read()

        # Replace the first occurrence of its prefix
        prod_obj_path = obj_path.replace(LEGACY_PATH_PREFIX, PRODUCTION_PATH_PREFIX, 1)
        # TODO: check failure cases?
        s3.put_object(
            Bucket=PRODUCTION_BUCKET_NAME,
            Body=legacy_obj,
            Key=prod_obj_path
        )
        update_ids.append(obj_id)

    # For benchmarking purposes, only commit on non-debug runs
    cursor.execute(update_query, (LEGACY_PATH_PREFIX, PRODUCTION_PATH_PREFIX, tuple(update_ids),))
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
