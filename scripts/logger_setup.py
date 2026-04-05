import logging
import os
import sys

from botocore.config import Config

from config import S3_ACCESS_KEY, S3_BUCKETNAME, S3_ENDPOINT, S3_REGION, S3_SECRET_KEY

sys.path.insert(0, os.path.dirname(__file__))

from helpers.observability.s3_log_handler import AsyncS3PipeHandler

# ── Logger ─────────────────────────────────────────────────────────────────────

def initialise_logger() -> None:
    """Create logger for running application"""
    client_params = {
        "aws_access_key_id": S3_ACCESS_KEY,
        "aws_secret_access_key": S3_SECRET_KEY,
        "region_name": S3_REGION,
        "endpoint_url": S3_ENDPOINT,
        "config": Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path'},    # addressing_style to be changed to virtual for AWS S3
            ) 
        }
    
    handler = AsyncS3PipeHandler(
        client_params=client_params,
        bucket_name=S3_BUCKETNAME,
        chunk_size=100*1024,
        filename="backend.log"
        )
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.propagate = True
    
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(handler)
   
    print("[Logger] Logging initialized.")
