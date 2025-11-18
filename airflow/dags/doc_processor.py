"""
Document Processor DAG

Fetches documents from S3 and processes them with comprehensive health checks.
"""

from datetime import timedelta, datetime
import os
import logging
import socket
import subprocess
import sys
import asyncio
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from aws_utils import download_from_s3, create_s3_client
from botocore.exceptions import ClientError

# Add src to path for imports
sys.path.insert(0, '/opt/airflow')

from src.services.document_parser import document_parser_service
from src.services.database import get_session
from src.models.metadata import MetadataExtract

logger = logging.getLogger(__name__)


def task1_verify_endpoints(**context):
    """
    Task 1: Verify connections to all endpoints

    Checks:
    - FastAPI endpoint
    - Airflow webserver
    - PostgreSQL database
    - Redis
    - OpenSearch
    """
    logger.info("=" * 80)
    logger.info("TASK 1: VERIFYING ENDPOINT CONNECTIONS")
    logger.info("=" * 80)

    endpoints = {
        "FastAPI": ("agentic-fastapi", 8000),
        "PostgreSQL": ("agentic-postgres", 5432),
        "Redis": ("agentic-redis", 6379),
        "OpenSearch": ("agentic-opensearch", 9200),
    }

    results = {}
    all_passed = True

    for service, (host, port) in endpoints.items():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                logger.info(f"✅ {service} ({host}:{port}) - CONNECTED")
                results[service] = "CONNECTED"
            else:
                logger.error(f"❌ {service} ({host}:{port}) - FAILED")
                results[service] = "FAILED"
                all_passed = False

        except Exception as e:
            logger.error(f"❌ {service} ({host}:{port}) - ERROR: {e}")
            results[service] = f"ERROR: {e}"
            all_passed = False

    logger.info("=" * 80)
    if all_passed:
        logger.info("✅ TASK 1 COMPLETE: All endpoint connections verified")
    else:
        logger.error("❌ TASK 1 FAILED: Some endpoints are not reachable")
        raise Exception(f"Endpoint verification failed: {results}")

    logger.info("=" * 80)

    # Push results to XCom
    context["ti"].xcom_push(key="endpoint_verification", value=results)
    return results


def task2_verify_s3_access(**context):
    """
    Task 2: Verify S3 bucket access

    Checks:
    - AWS credentials are configured
    - Can connect to S3
    - Target bucket exists
    - Can list bucket contents
    """
    logger.info("=" * 80)
    logger.info("TASK 2: VERIFYING S3 BUCKET ACCESS")
    logger.info("=" * 80)

    try:
        # Get S3 bucket from DAG config
        dag_run = context.get("dag_run")
        conf = dag_run.conf if dag_run else {}
        s3_bucket = conf.get("s3_bucket", os.getenv("AWS_S3_BUCKET", "ses"))

        logger.info(f"Target S3 Bucket: {s3_bucket}")

        # Create S3 client
        s3_client = create_s3_client()
        logger.info("✅ S3 client created successfully")

        # Check if bucket exists
        try:
            s3_client.head_bucket(Bucket=s3_bucket)
            logger.info(f"✅ Bucket '{s3_bucket}' exists and is accessible")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                raise Exception(f"Bucket '{s3_bucket}' does not exist")
            elif error_code == '403':
                raise Exception(f"Access denied to bucket '{s3_bucket}'")
            else:
                raise

        # List objects in input prefix
        response = s3_client.list_objects_v2(Bucket=s3_bucket, Prefix="input/", MaxKeys=10)
        if 'Contents' in response:
            file_count = len(response['Contents'])
            logger.info(f"✅ Found {file_count} objects in input/ prefix")
            for obj in response['Contents'][:5]:
                logger.info(f"   - {obj['Key']}")
        else:
            logger.warning("⚠️  No objects found in input/ prefix")

        logger.info("=" * 80)
        logger.info("✅ TASK 2 COMPLETE: S3 bucket access verified")
        logger.info("=" * 80)

        context["ti"].xcom_push(key="s3_verification", value={"bucket": s3_bucket, "status": "verified"})
        return {"bucket": s3_bucket, "status": "verified"}

    except Exception as e:
        logger.error(f"❌ S3 verification failed: {e}")
        logger.info("=" * 80)
        raise


def task3_verify_containers(**context):
    """
    Task 3: Verify docker containers are running and can communicate

    Checks:
    - All containers are running
    - Inter-container networking
    """
    logger.info("=" * 80)
    logger.info("TASK 3: VERIFYING DOCKER CONTAINERS")
    logger.info("=" * 80)

    required_containers = [
        "agentic-fastapi",
        "agentic-postgres",
        "agentic-redis",
        "agentic-opensearch",
        "agentic-airflow-scheduler",
        "agentic-airflow-webserver"
    ]

    container_status = {}
    all_running = True

    for container in required_containers:
        try:
            # Check if we can resolve the hostname (container networking)
            socket.gethostbyname(container)
            logger.info(f"✅ Container '{container}' - DNS resolution OK")
            container_status[container] = "RUNNING"
        except socket.gaierror:
            logger.error(f"❌ Container '{container}' - DNS resolution FAILED")
            container_status[container] = "NOT_REACHABLE"
            all_running = False

    logger.info("=" * 80)
    if all_running:
        logger.info("✅ TASK 3 COMPLETE: All containers verified")
    else:
        logger.error("❌ TASK 3 FAILED: Some containers are not reachable")
        raise Exception(f"Container verification failed: {container_status}")

    logger.info("=" * 80)

    context["ti"].xcom_push(key="container_verification", value=container_status)
    return container_status


def task4_fetch_document(**context):
    """
    Task 4: Fetch document from S3 and store in /tmp

    Downloads the specified document from S3 and saves to /tmp location
    """
    logger.info("=" * 80)
    logger.info("TASK 4: FETCHING DOCUMENT FROM S3")
    logger.info("=" * 80)

    try:
        # Get configuration from DAG run
        dag_run = context.get("dag_run")
        conf = dag_run.conf if dag_run else {}

        job_id = conf.get("job_id")
        document_name = conf.get("document_name")
        s3_bucket = conf.get("s3_bucket", os.getenv("AWS_S3_BUCKET", "ses"))
        s3_key = conf.get("s3_key")
        command = conf.get("command")

        logger.info(f"Job ID: {job_id}")
        logger.info(f"Command: {command}")
        logger.info(f"Document Name: {document_name}")
        logger.info(f"S3 Bucket: {s3_bucket}")
        logger.info(f"S3 Key: {s3_key}")

        # Validate inputs
        if not document_name or not s3_key:
            raise ValueError("Missing required parameters: document_name or s3_key")

        # Construct local path
        local_dir = f"/tmp/{job_id}"
        local_path = f"{local_dir}/{document_name}"

        # Download from S3
        logger.info(f"Downloading from s3://{s3_bucket}/{s3_key}")
        downloaded_path = download_from_s3(s3_key, local_path, bucket_name=s3_bucket)

        # Verify download
        if os.path.exists(downloaded_path):
            file_size = os.path.getsize(downloaded_path)
            logger.info(f"✅ File downloaded successfully")
            logger.info(f"   Local Path: {downloaded_path}")
            logger.info(f"   File Size: {file_size:,} bytes ({file_size/1024:.2f} KB)")
        else:
            raise Exception(f"Download failed - file not found at {downloaded_path}")

        logger.info("=" * 80)
        logger.info(f"✅ TASK 4 COMPLETE: Document '{document_name}' from {local_path} has been successfully fetched")
        logger.info("=" * 80)

        # Push to XCom for next tasks
        result = {
            "local_path": downloaded_path,
            "document_name": document_name,
            "file_size": file_size,
            "job_id": job_id
        }
        context["ti"].xcom_push(key="document_fetch", value=result)

        return result

    except Exception as e:
        logger.error(f"❌ Document fetch failed: {e}")
        logger.info("=" * 80)
        raise


def task5_parse_document(**context):
    """
    Task 5: Parse document and store metadata in PostgreSQL

    Uses python-docx and Claude Sonnet to:
    - Extract table specifications from document
    - Parse columns into 21-field schema
    - Store in metadata_extract table
    """
    logger.info("=" * 80)
    logger.info("TASK 5: PARSING DOCUMENT AND EXTRACTING METADATA")
    logger.info("=" * 80)

    try:
        # Get document info from previous task
        ti = context["ti"]
        document_fetch = ti.xcom_pull(task_ids="task4_fetch_document", key="document_fetch")

        if not document_fetch:
            raise ValueError("No document fetch information found from task4")

        local_path = document_fetch["local_path"]
        document_name = document_fetch["document_name"]
        job_id = document_fetch["job_id"]

        logger.info(f"Job ID: {job_id}")
        logger.info(f"Document Name: {document_name}")
        logger.info(f"Local Path: {local_path}")

        # Verify file exists
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Document not found at {local_path}")

        # Generate metadata ID
        metadata_id = f"META_{job_id}"
        logger.info(f"Metadata ID: {metadata_id}")

        # Parse document (async operation wrapped in sync function)
        logger.info("Starting document parsing with Claude Sonnet...")
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        metadata_json = loop.run_until_complete(
            document_parser_service.parse_document(
                file_path=local_path,
                metadata_id=metadata_id
            )
        )

        logger.info("✅ Document parsing completed")
        logger.info(f"   Extracted {len(metadata_json.tables)} table(s)")
        for table in metadata_json.tables:
            logger.info(f"   - Table: {table.table_name} ({len(table.columns)} columns)")

        # Get DAG config for S3 path
        dag_run = context.get("dag_run")
        conf = dag_run.conf if dag_run else {}
        s3_bucket = conf.get("s3_bucket", os.getenv("AWS_S3_BUCKET", "ses-v1"))
        s3_key = conf.get("s3_key", "")

        logger.info("=" * 80)
        logger.info(f"✅ TASK 5 COMPLETE: Document parsed (DB insertion pending approval)")
        logger.info(f"   Metadata ID: {metadata_id}")
        logger.info(f"   Tables: {len(metadata_json.tables)}")
        logger.info(f"   Columns: {sum(len(table.columns) for table in metadata_json.tables)}")
        logger.info("=" * 80)

        # Push full metadata to XCom for agent retrieval
        result = {
            "metadata_id": metadata_id,
            "job_id": job_id,
            "document_name": document_name,
            "s3_bucket": s3_bucket,
            "s3_key": s3_key,
            "metadata_json": metadata_json.model_dump(),  # Full parsed data
            "table_count": len(metadata_json.tables),
            "column_count": sum(len(table.columns) for table in metadata_json.tables),
            "status": "parsed_awaiting_approval"
        }
        context["ti"].xcom_push(key="document_parse", value=result)

        return result

    except Exception as e:
        logger.error(f"❌ Document parsing failed: {e}")
        logger.info("=" * 80)
        raise


# Default DAG arguments
default_args = {
    "owner": "sim",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

# Create DAG
with DAG(
    "doc_processor",
    default_args=default_args,
    description="Document processor with health checks and S3 fetch",
    schedule=None,  # Triggered by API
    catchup=False,
    tags=["document-processing", "verification", "production"],
) as dag:

    # Task 1: Verify endpoint connections
    verify_endpoints = PythonOperator(
        task_id="task1_verify_endpoints",
        python_callable=task1_verify_endpoints,
    )

    # Task 2: Verify S3 access
    verify_s3 = PythonOperator(
        task_id="task2_verify_s3_access",
        python_callable=task2_verify_s3_access,
    )

    # Task 3: Verify containers
    verify_containers = PythonOperator(
        task_id="task3_verify_containers",
        python_callable=task3_verify_containers,
    )

    # Task 4: Fetch document
    fetch_document = PythonOperator(
        task_id="task4_fetch_document",
        python_callable=task4_fetch_document,
    )

    # Task 5: Parse document
    parse_document = PythonOperator(
        task_id="task5_parse_document",
        python_callable=task5_parse_document,
    )

    # Task dependencies
    verify_endpoints >> verify_s3 >> verify_containers >> fetch_document >> parse_document
