"""
Hello World S3 DAG

Simple test DAG to verify S3 connectivity and Airflow setup.
Validates AWS credentials, S3 access, and Bedrock API connectivity.
"""

from datetime import timedelta, datetime

from airflow.operators.python import PythonOperator
from aws_utils import list_s3_buckets, verify_bedrock_access

from airflow import DAG

default_args = {
    "owner": "sim",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
}


with DAG(
    "hello_world_s3_dag",
    default_args=default_args,
    description="Test DAG for S3 and AWS connectivity",
    schedule=None,
    catchup=False,
    tags=["test", "hello-world"],
) as dag:

    s3_task = PythonOperator(
        task_id="list_s3_buckets",
        python_callable=list_s3_buckets,
    )

    bedrock_task = PythonOperator(
        task_id="verify_bedrock_access",
        python_callable=verify_bedrock_access,
    )

    s3_task >> bedrock_task
